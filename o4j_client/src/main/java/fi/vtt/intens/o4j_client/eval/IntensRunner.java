package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.InterruptedIOException;
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

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import eu.cityopt.sim.eval.SimulationFailure;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationResults;
import eu.cityopt.sim.eval.SimulationRunner;
import eu.cityopt.sim.eval.Type;
import io.socket.client.IO;
import io.socket.client.Socket;
import okhttp3.HttpUrl;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;

public class IntensRunner implements SimulationRunner {
    private static Logger logger = LoggerFactory.getLogger(IntensRunner.class);
    public final IntensModel model;
    public ObjectMapper om;
    public OkHttpClient http;
    private Socket sio;
    // Jobs that we are waiting for.
    private Map<Integer, IntensJob> jobs = new ConcurrentHashMap<>();

    // Terminated jobs for which result retrieval has failed.
    private Map<Integer, IntensJob> error_jobs = new ConcurrentHashMap<>();

    /**
     * Fetch statuses of given jobs from the server.
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
                        logger.warn("Job {} lost from server", j);
                        st.put(j, JobStatus.INVALID);
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
                            logger.warn("Termination event lost on job {}",
                                        ent.getKey());
                            completeJob(ent.getValue(), job);
                        }
                    }
                } catch (InterruptedException | InterruptedIOException e){
                    currentThread().interrupt();
                    return;
                } catch (IOException e) {
                    logger.warn("Error in periodic status update", e);
                }
            }
        }
    }
    private Thread updateThread = null;

    private synchronized void startUpdate() {
        if (updateThread != null) {
            if (updateThread.isAlive())
                return;
            else
                logger.error("Periodic update thread has died");
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

    /**
     * Attempt to parse a JsonNode as a sim-eval type.
     * @throws JsonProcessingException if json is of incompatible type
     * @throws IllegalArgumentException if elements of json are of incompatible
     *   type (when parsing a list) or if type is unsupported.
     */
    private Object parseResult(Type type, JsonNode json)
            throws IOException {
        switch(type) {
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
                                parseResult(out_kv.getValue(), val));
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
     * @return whether job has completed.
     */
    public boolean getJobStatus(IntensJob job) {
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
                try {
                    completeJob(st, job);
                } catch (IOException e) {
                    error_jobs.put(job.jobid, job);
                }
                return true;
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

    private synchronized void connect_sio() throws InterruptedException {
        sio.connect();
        while (!sio.connected())
            wait();
    }

    private void on_terminated(Object... args) {
        TerminatedData arg;
        try {
            arg = om.convertValue(args[0], TerminatedData.class);
        } catch (IllegalArgumentException e) {
            logger.error("on_terminated: invalid payload " + args[0]);
            return;
        }
        IntensJob job = jobs.remove(arg.job);
        if (job != null) {
            try {
                completeJob(arg.status, job);
            } catch (IOException e) {
                error_jobs.put(arg.job, job);
                logger.error(
                        "on_terminated: IO exception on job " + arg.job, e);
            }
        }
    }

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
                var sslc = SSLContext.getInstance("TLS");
                var tms = tmf.getTrustManagers();
                if (tms.length != 1)
                    throw new IllegalStateException(
                            "No or multiple trust managers: "
                            + Arrays.toString(tms));
                sslc.init(null, tms, null);
                bld = bld.sslSocketFactory(sslc.getSocketFactory(),
                                           (X509TrustManager)tms[0]);
            } catch (IOException | GeneralSecurityException e) {
                throw new RuntimeException("SSL configuration error", e);
            }
        }
        if (model.auth != null) {
            bld = bld.authenticator(model.auth);
        }
        http = bld.build();
        var opts = new IO.Options();
        opts.callFactory = http;
        opts.webSocketFactory = http;
//        opts.transports = new String[] {"websocket"};
        sio = IO.socket(model.uri, opts);
        sio.on("terminated", this::on_terminated);
        sio.on(Socket.EVENT_CONNECT, this::on_connect);
        sio.on(Socket.EVENT_ERROR, this::on_error);
        sio.on(Socket.EVENT_CONNECT_ERROR, this::on_error);
        try {
            connect_sio();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Socket.IO connection interrupted", e);
        }
    }

    @Override
    public synchronized void close() throws IOException {
        if (updateThread != null && updateThread.isAlive()) {
            updateThread.interrupt();
        }
        if (sio.connected()) {
            sio.close();
        }
        if (!jobs.isEmpty()) {
            logger.warn("Closing runner with " + jobs.size() + " active jobs");
        }
    }

    static final MediaType json_mt = MediaType.parse("application/json");

    @Override
    public IntensJob start(SimulationInput input) throws IOException {
        startUpdate();
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
        try (var resp = http.newCall(req).execute()) {
            if (resp.code() != HTTP_CREATED)
                throw new HttpException(resp);
            int jobid = om.readValue(resp.body().string(), Integer.class);
            var job = new IntensJob(jobid, input);
            getJobStatus(job);
            return job;
        }
    }
}
