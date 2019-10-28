package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.nio.file.Files;
import java.security.GeneralSecurityException;
import java.security.KeyStore;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;

import static java.net.HttpURLConnection.*;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import eu.cityopt.sim.eval.Evaluator;
import eu.cityopt.sim.eval.SimulationFailure;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationResults;
import eu.cityopt.sim.eval.SimulationRunner;
import eu.cityopt.sim.eval.TimeSeriesI;
import eu.cityopt.sim.eval.Type;
import io.socket.client.IO;
import io.socket.client.Socket;
import okhttp3.HttpUrl;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;

/**
 * A SimulationRunner for Simsvc.
 * Connects to a Simsvc instance and runs jobs there.
 * @author ttekth
 *
 */
public class IntensRunner implements SimulationRunner {
    private static Logger logger = LoggerFactory.getLogger(IntensRunner.class);
    public final IntensModel model;
    public ObjectMapper om;
    public OkHttpClient http;
    private Socket sio;
    // Jobs that we are waiting for.
    private Map<Integer, IntensJob> jobs = new ConcurrentHashMap<>();

    /**
     * Fetch statuses of given jobs from the server.
     * It is possible that some jobs in jids are missing from the result
     * if they were not found on the server.  This should not happen but
     * sometimes does.
     * @param jids Job ids to fetch, null for all
     */
    public Map<Integer, JobStatus> getStatuses(Collection<Integer> jids)
            throws IOException {
        if (jids.isEmpty())
            return Collections.emptyMap();
        String only = jids.stream()
                .map(i -> i.toString())
                .collect(Collectors.joining(","));
        var url = HttpUrl.get(model.uri).newBuilder("jobs/")
                .addQueryParameter("status", "true")
                .addQueryParameter("only", only).build();
        var req = new Request.Builder().url(url).build();
        try (var resp = http.newCall(req).execute()) {
            switch (resp.code()) {
            case HTTP_OK:
                Map<Integer, JobStatus> st = om.readValue(
                        resp.body().charStream(),
                        new TypeReference<Map<Integer, JobStatus>>() {});
                for (int j : jids) {
                    if (!st.containsKey(j)) {
                        logger.warn("Job {} missing from server response", j);
                    }
                }
                return st;
            default:
                throw new HttpException(resp);
            }
        }
    }

    private class UpdateThread extends Thread {
        int period = 30000;

        @Override
        public void run() {
            for (;;) {
                try {
                    sleep(period);
                    var stats = getStatuses(jobs.keySet());
                    for (var ent : stats.entrySet()) {
                        IntensJob job;
                        if (!ent.getValue().isActive()
                            && (job = jobs.remove(ent.getKey())) != null) {
                            if (job.fetchFailures == 0)
                                logger.warn(
                                        "Termination event lost for job {}",
                                        ent.getKey());
                            tryCompleteJob(ent.getValue(), job);
                        }
                    }
                } catch (InterruptedException e){
                    logger.error("Periodic update thread interrupted", e);
                    currentThread().interrupt();
                    return;
                } catch (IOException e) {
                    logger.warn("Error in periodic status update", e);
                }
            }
        }

        private void excHandler(Throwable exc) {
            logger.error("Periodic update thread died", exc);
        }

        public UpdateThread() {
            super("IntensRunner.UpdateThread");
            setUncaughtExceptionHandler((t, e) -> excHandler(e));
        }
    }
    private Thread updateThread = null;

    private synchronized void startUpdate() {
        if (updateThread != null) {
            if (updateThread.isAlive())
                return;
            else
                logger.warn("Restarting periodic update thread");
        }
        updateThread = new UpdateThread();
        updateThread.setDaemon(true);
        updateThread.start();
    }

    public String getLog(int jobid) throws IOException {
        if (model.logFile == null)
           return null;
        var uri = HttpUrl.get(model.uri).resolve("jobs/" + jobid + "/files/")
                .resolve(model.logFile);
        var req = new Request.Builder().url(uri).build();
        try (var resp = http.newCall(req).execute()) {
            switch (resp.code()) {
            case HTTP_OK:
                return resp.body().string();
            case HTTP_NOT_FOUND:
                return null;
            default:
                throw new HttpException(resp);
            }
        }
    }

    private class TimeSeriesParser {
        Evaluator ev;
        ObjectNode root;
        Map<String, double[]> times = new HashMap<>();

        TimeSeriesParser(Evaluator ev, ObjectNode root) {
            this.ev = ev;
            this.root = root;
        }

        synchronized double[] getTimes(String tnam) throws IOException {
            double[] t = times.get(tnam);
            if (t == null) {
                var tn2 = root.get(tnam);
                if (tn2 == null)
                    throw new IllegalArgumentException(
                            "Referenced time values missing: "
                            + tnam);
                t = om.treeToValue(tn2, double[].class);
                times.put(tnam, t);
            }
            return t;
        }

        TimeSeriesI parse(Type type, JsonNode val) throws IOException {
            ObjectNode obj;
            try {
                obj = (ObjectNode)val;
            } catch (ClassCastException e) {
                throw new IllegalArgumentException(
                        "Time series not a JSON object", e);
            }
            JsonNode
                tn = obj.get("times"),
                vn = obj.get("values");
            if (tn == null || vn == null)
                throw new IllegalArgumentException(
                        "Times or values missing from time series");
            double[]
                t = tn.isArray()
                    ? om.treeToValue(tn, double[].class)
                    : getTimes(om.treeToValue(tn, String.class)),
                vals = om.treeToValue(val, double[].class);
            return ev.makeTS(type, t, vals);
        }
    }

    /**
     * Attempt to parse a JsonNode as a sim-eval type.
     * @throws JsonProcessingException if json is of incompatible type
     * @throws IllegalArgumentException if elements of json are of incompatible
     *   type (when parsing a list) or if type is unsupported.
     */
    private Object parseResult(Type type, JsonNode json, TimeSeriesParser tsp)
            throws IOException {
        switch (type) {
        case DOUBLE:
        case TIMESTAMP:
            return om.treeToValue(json, Double.class);
        case INTEGER:
            return om.treeToValue(json, Integer.class);
        case STRING:
            return om.treeToValue(json, String.class);
        case LIST_OF_DOUBLE:
        case LIST_OF_INTEGER:
        case LIST_OF_TIMESTAMP:
            @SuppressWarnings("unchecked")
            List<Object> val = om.treeToValue(json, List.class);
            if (!type.isCompatible(val))
                throw new IllegalArgumentException(
                        "Incompatible list for " + type + ": " + json);
            return val;
        case TIMESERIES_LINEAR:
        case TIMESERIES_STEP:
            return tsp.parse(type, json);
        default:
            throw new IllegalArgumentException("Unsupported type " + type);
        }
    }

    /**
     * Retrieve simulation results and complete job with them.
     * Should only be called for successfully terminated simulations.
     * @param job Job to fetch results for
     * @throws HttpException on HTTP errors
     * @throws IOException on other I/O errors, e.g., JSON parsing
     */
    private void getResults(IntensJob job) throws IOException {
        var res = new SimulationResults(job.input, getLog(job.jobid));
        var ns = job.input.getNamespace();
        String only = ns.components.entrySet().stream()
                    .flatMap(kv -> kv.getValue().outputs.keySet().stream().map(
                                     op -> kv.getKey() + "." + op))
                    .collect(Collectors.joining(","));
        var uri = HttpUrl.get(model.uri)
                .newBuilder("jobs/" + job.jobid + "/results/")
                .addQueryParameter("only", only).build();
        var req = new Request.Builder().url(uri).build();
        try (var resp = http.newCall(req).execute()) {
            if (resp.code() != HTTP_OK)
                throw new HttpException(resp);
            var root = (ObjectNode)om.readTree(resp.body().charStream());
            var tsp = new TimeSeriesParser(res.getNamespace().evaluator, root);
            for (var comp_kv : ns.components.entrySet()) {
                String comp = comp_kv.getKey();
                for (var out_kv : comp_kv.getValue().outputs.entrySet()) {
                    String
                        out = out_kv.getKey(),
                        qname = comp + "." + out;
                    var val = root.get(qname);
                    if (val == null)
                        throw new IOException(
                                "Missing value from response: "+ qname);
                    else
                        res.put(comp, out,
                                parseResult(out_kv.getValue(), val, tsp));
                }
            }
        } catch (ClassCastException e) {
            throw new IOException("getResults: response not a JSON object", e);
        } catch (IllegalArgumentException e) {
            throw new IOException("getResults: type conversion failed", e);
        }
        job.complete(res);
    }

    /**
     * Retrieve the error message of job and complete job with it.
     * Should only be called for failed jobs.
     */
    private void getError(IntensJob job) throws IOException {
        var uri = HttpUrl.get(model.uri).resolve(
                "jobs/" + job.jobid + "/error");
        var req = new Request.Builder().url(uri).build();
        try (var resp = http.newCall(req).execute()) {
            if (resp.code() != HTTP_OK)
                throw new HttpException(resp);
            String msg = om.readValue(resp.body().charStream(), String.class);
            job.complete(new SimulationFailure(
                    job.input, true, msg, getLog(job.jobid)));
        }
    }

    /**
     * Complete job according to st.
     * To be called when the server indicates that job has terminated with
     * status st.
     * @throws IOException on possibly transient I/O errors
     */
    private void completeJob(JobStatus st, IntensJob job) throws IOException {
        try {
            switch (st) {
            case DONE:
                getResults(job);
                return;
            case FAILED:
                getError(job);
                return;
            case CANCELLED:
                job.set_cancelled();
                return;
            default:
                job.complete(new SimulationFailure(
                        job.input, false,
                        "Abnormal job status " + st, getLog(job.jobid)));
                return;
            }
        } catch (HttpException e) {
            // This may get better by itself.  Assume nothing else will.
            if (e.httpStatus == HTTP_UNAVAILABLE)
                throw e;
            job.complete(new SimulationFailure(
                    job.input, true, "HTTP status " + e.httpStatus,
                    e.getMessage()));
        }
    }

    /**
     * Like {@link #completeJob} but handles exceptions.
     * On IOException job is added to jobs, causing UpdateThread
     * to retry it.  The error count of the job is incremented and an
     * error message is logged.
     */
    private void tryCompleteJob(JobStatus status, IntensJob job) {
        try {
            completeJob(status, job);
        } catch (IOException e) {
            job.fetchFailures++;
            jobs.put(job.jobid, job);
            if (e instanceof SocketTimeoutException) {
                logger.warn("tryCompleteJob: timeout on job {}, "
                        + "attempt {}", job.jobid, job.fetchFailures);
            } else {
                logger.error("tryCompleteJob: IO exception on job {}, "
                        + "attempt {}", job.jobid, e);
            }
        }
    }

    /**
     * Like {@link #tryCompleteJob(JobStatus, IntensJob)} but gets the
     * job from jobs, removing it.  It is put back if there is an error.
     * No-op if jobid was not in jobs.
     */
    private void tryCompleteJob(JobStatus status, int jobid) {
        IntensJob job = jobs.remove(jobid);
        if (job != null)
            tryCompleteJob(status, job);
    }

    /**
     * Query the server for the status of job.  If active (not terminated)
     * arrange job to be waited for and return false.  Otherwise complete job
     * (with {@link #completeJob(JobStatus, IntensJob)}), remove it from
     * waited jobs, and return true.  HTTP_NOT_FOUND (404) for the job
     * status request completes the job as failure.  Other HTTP or I/O errors
     * cause the job to be regarded active: false is returned and the
     * job continues to be waited for.  If an error occurs in completeJob, job
     * will be added to error_jobs.
     *
     * Do nothing if job was already completed.
     *
     * @param job The {@link IntensJob} to update
     * @param allowMissing If job is not found on the server consider it
     *   as still active (true) rather than failed (false).
     * @return whether job has completed.
     */
    public boolean getJobStatus(IntensJob job, boolean allowMissing) {
        if (job.isDone()) {
            jobs.remove(job.jobid);
            return true;
        } else {
            jobs.put(job.jobid, job);
        }
        var uri = HttpUrl.get(model.uri).resolve("jobs/" + job.jobid);
        var req = new Request.Builder().url(uri).build();
        try (var resp = http.newCall(req).execute()) {
            switch (resp.code()) {
            case HTTP_NOT_FOUND:
                if (allowMissing) {
                    logger.warn("Job {} not found on server", job.jobid);
                    return false;
                }
                jobs.remove(job.jobid, job);
                job.complete(new SimulationFailure(
                        job.input, false, "Deleted from server",
                        resp.body().string()));
                return true;
            case HTTP_OK:
                var st = om.readValue(resp.body().charStream(),
                                      JobStatus.class);
                if (st.isActive())
                    return false;
                jobs.remove(job.jobid);
                tryCompleteJob(st, job);
                return job.isDone();
            default:
                throw new HttpException(resp);
            }
        } catch (IOException e) {
            logger.error("Error getting job status", e);
            return false;
        }
    }

    public static class TerminatedData {
        public int job;
        public JobStatus status;
    }

    private synchronized void on_connect(Object... args) {
        notifyAll();
    }

    private void on_error(Object... args) {
        if (args.length == 1 && args[0] instanceof Exception) {
            logger.error("Socket.IO error", (Exception)args[0]);
        } else {
            logger.error("Socket.IO error: {}", Arrays.asList(args));
        }
    }

    private synchronized void on_timeout(Object... args) {
        logger.error("Socket.IO timeout: {}", Arrays.asList(args));
        sio.close();
        sio = null;
        notifyAll();
    }

    private synchronized void waitSioConnect() throws IOException {
        try {
            for (;;) {
                if (sio == null)
                    throw new IOException("Socket.IO connection timed out");
                else if (sio.connected())
                    return;
                logger.info("Waiting for Socket.IO connection");
                wait();
            }
        } catch (InterruptedException e) {
            sio.close();
            sio = null;
            Thread.currentThread().interrupt();
            throw new IOException("Socket.IO connection interrupted", e);
        }
    }

    private void on_terminated(Object... args) {
        TerminatedData arg;
        try {
            arg = om.convertValue(args[0], TerminatedData.class);
        } catch (IllegalArgumentException e) {
            logger.error("on_terminated: invalid payload " + args[0]);
            return;
        }
        tryCompleteJob(arg.status, arg.job);
    }

    /**
     * Construct a runner for the given model and connect with Socket.IO.
     * Does not wait for the Socket.IO connection to be established.
     * {@link #start(SimulationInput)} does that.
     * @param model Defines the Simsvc connection details.
     */
    public IntensRunner(IntensModel model) throws IOException {
        this.model = model;
        om = model.getSimulatorManager().protocolOM;
        var bld = new OkHttpClient.Builder();
        if (model.cafile != null) {
            /* All this to read trusted CA certs from a file!
               API from hell. */
            try (var ca = Files.newInputStream(model.cafile)) {
                var ks = KeyStore.getInstance(KeyStore.getDefaultType());
                ks.load(null, null);
                for (var cert : CertificateFactory.getInstance("X.509")
                        .generateCertificates(ca)) {
                    var x509 = (X509Certificate)cert;
                    ks.setCertificateEntry(
                            x509.getSubjectDN().toString(), x509);
                }
                var tmf = TrustManagerFactory.getInstance(
                        TrustManagerFactory.getDefaultAlgorithm());
                tmf.init(ks);
                var tms = tmf.getTrustManagers();
                if (tms.length != 1)
                    throw new IllegalStateException(
                            "No or multiple trust managers: "
                            + Arrays.toString(tms));
                var sslc = SSLContext.getInstance("TLS");
                sslc.init(null, tms, null);
                bld = bld.sslSocketFactory(sslc.getSocketFactory(),
                                           (X509TrustManager)tms[0]);
            } catch (GeneralSecurityException e) {
                throw new IOException("SSL configuration error", e);
            }
        }
        if (model.auth != null) {
            bld = bld.authenticator(model.auth);
        }
        http = bld.build();
        var opts = new IO.Options();
        opts.callFactory = http;
        opts.webSocketFactory = http;
//      opts.transports = new String[] {"websocket"};
        /*XXX IO.socket treats the URI rather strangely:
         * its path is interpreted as a Socket.IO namespace but
         * connection is to uri.resolve(opts.path).  opts.path must begin
         * with a slash (default /socket.io), thus the original URI path
         * is removed from the connection URI.
         *
         * However, we want to connect to uri.resolve("socket.io"), i.e.,
         * relative to the original path, root namespace.
         */
        opts.path = model.uri.resolve("socket.io").getRawPath();
        sio = IO.socket(model.uri.resolve("/"), opts);
        sio.on("terminated", this::on_terminated);
        sio.on(Socket.EVENT_CONNECT, this::on_connect);
        sio.on(Socket.EVENT_ERROR, this::on_error);
        sio.on(Socket.EVENT_CONNECT_ERROR, this::on_error);
        sio.on(Socket.EVENT_CONNECT_TIMEOUT, this::on_timeout);
        sio.connect();
    }

    @Override
    public synchronized void close() throws IOException {
        if (!jobs.isEmpty()) {
            logger.warn("Closing runner with " + jobs.size() + " active jobs");
            for (var job : jobs.values()) {
                job.cancel(true);
            }
        }
        if (updateThread != null && updateThread.isAlive()) {
            updateThread.interrupt();
        }
        if (sio != null) {
            sio.close();
            sio = null;
        }
    }

    static final MediaType json_mt = MediaType.parse("application/json");

    @Override
    public IntensJob start(SimulationInput input) throws IOException {
        startUpdate();
        waitSioConnect();
        Map<String, Object> binds = new HashMap<>();
        var ns = input.getNamespace();
        for (var comp_kv : ns.components.entrySet()) {
            var comp = comp_kv.getKey();
            for (var inp_kv : comp_kv.getValue().inputs.entrySet()) {
                var inp = inp_kv.getKey();
                switch (inp_kv.getValue()) {
                default:
                    throw new IOException(
                            "Unsupported type " + inp_kv.getValue());
                case DOUBLE:
                case TIMESTAMP:
                case INTEGER:
                case STRING:
                case LIST_OF_DOUBLE:
                case LIST_OF_INTEGER:
                case LIST_OF_TIMESTAMP:
                    binds.put(comp + "." + inp, input.get(comp, inp));
                }
            }
        }
        var uri = HttpUrl.get(model.uri).resolve("jobs/");
//        om.disable(JsonGenerator.Feature.AUTO_CLOSE_TARGET);
//        var body = new FunctionalBody(json_mt,
//                                      out -> om.writeValue(out, binds));
        var body = RequestBody.create(json_mt, om.writeValueAsString(binds));
        var req = new Request.Builder().url(uri).post(body).build();
        int jobid;
        for (;;) {
            try (var resp = http.newCall(req).execute()) {
                if (resp.code() != HTTP_CREATED)
                    throw new HttpException(resp);
                jobid = om.readValue(resp.body().string(), Integer.class);
                break;
            } catch (SocketTimeoutException e) {
                logger.warn("Timeout posting job");
            }
        }
        var job = new IntensJob(jobid, input);
        getJobStatus(job, true);
        return job;
    }
}
