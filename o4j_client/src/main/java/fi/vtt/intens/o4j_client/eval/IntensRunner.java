package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.URLEncoder;

import static java.net.HttpURLConnection.*;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse.BodyHandlers;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.common.io.CharStreams;

import eu.cityopt.sim.eval.SimulationFailure;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationResults;
import eu.cityopt.sim.eval.SimulationRunner;
import eu.cityopt.sim.eval.Type;
import io.socket.client.IO;
import io.socket.client.Socket;

public class IntensRunner implements SimulationRunner {
    private static Logger logger = LoggerFactory.getLogger(IntensRunner.class);
    public final IntensModel model;
    public ObjectMapper om;
    public HttpClient http;
    private Socket sio;
    // Jobs that we are waiting for.
    private Map<Integer, IntensJob> jobs = new ConcurrentHashMap<>();
    
    // Jobs that we have failed to retrieve results for.
    private Map<Integer, IntensJob> error_jobs = new ConcurrentHashMap<>();

    public String getLog(int jobid) throws IOException, InterruptedException {
        if (model.logFile == null)
           return null;
        var uri = model.uri.resolve("jobs/" + jobid + "/files/")
                .resolve(model.logFile);
        var req = HttpRequest.newBuilder(uri).build();
        var resp = http.send(req, BodyHandlers.ofString());
        switch (resp.statusCode()) {
        case HTTP_OK:
            return resp.body();
        case HTTP_NOT_FOUND:
            return null;
        default:
            throw new HttpException(resp.statusCode(), resp.body());
        }
    }
    
    /**
     * Attempt to parse a JsonNode as a sim-eval type.
     * @throws JsonParseException if json is of incompatible type
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

    private void getResults(int jobid, IntensJob job)
            throws IOException, InterruptedException {
        var res = new SimulationResults(job.input, getLog(jobid));
        var ns = job.input.getNamespace();
        String only = ns.components.entrySet().stream()
                    .flatMap(kv -> kv.getValue().outputs.keySet().stream().map(
                                     op -> kv.getKey() + "." + op))
                    .collect(Collectors.joining(","));
        var uri = model.uri.resolve("jobs/" + jobid + "/results/?only="
                                    + URLEncoder.encode(only, "UTF-8"));
        var req = HttpRequest.newBuilder(uri).build();
        var resp = http.send(req, BodyHandlers.ofInputStream());
        try (var body = new InputStreamReader(resp.body())) {
            if (resp.statusCode() != HTTP_OK)
                throw new HttpException(resp.statusCode(),
                                        CharStreams.toString(body));
            var root = (ObjectNode)om.readTree(body);
            for (var comp_kv : ns.components.entrySet()) {
                String comp = comp_kv.getKey();
                for (var out_kv : comp_kv.getValue().outputs.entrySet()) {
                    String
                        out = out_kv.getKey(),
                        qname = comp + "." + out;
                    var val = root.get(qname);
                    if (val == null)
                        logger.error("Missing value from response: "+ qname);
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

    private void getError(int jobid, IntensJob job)
            throws IOException, InterruptedException {
        URI err_uri = model.uri.resolve("jobs/" + jobid + "/error");
        var req = HttpRequest.newBuilder(err_uri).build();
        var resp = http.send(req, BodyHandlers.ofString());
        if (resp.statusCode() != HTTP_OK)
            throw new HttpException(resp.statusCode(),resp.body());
        String msg = om.readValue(resp.body(), String.class);
        job.complete(new SimulationFailure(
                job.input, true, msg, getLog(jobid)));
    }

    private void completeJob(int jobid, JobStatus st, IntensJob job)
            throws IOException, InterruptedException {
        switch (st) {
        case DONE:
            getResults(jobid, job);
            return;
        case FAILED:
            getError(jobid, job);
            return;
        case CANCELLED:
            job.set_cancelled();
            return;
        default:
            job.complete(new SimulationFailure(
                    job.input, false,
                    "Abnormal job status " + st, getLog(jobid)));
            return;
        }
    }
    
    /**
     * Query the server for the status of job <code>jobid</code>.  If it has
     * completed (successfully or not), complete <code>job</code> accordingly.
     * Otherwise put <code>(jobid, job)</code> in the waiting map, to be
     * updated when the server announces its termination over Socket.IO.
     * 
     * Do nothing if <code>job</code> was already completed.
     * 
     * @param jobid The job id on the server
     * @param job The {@link IntensJob} to update
     * @return whether job has completed.
     */
    public boolean getJobStatus(int jobid, IntensJob job)
            throws IOException, InterruptedException {
        URI job_uri = model.uri.resolve("jobs/" + jobid + "/");
        var req = HttpRequest.newBuilder(job_uri).build();
        if (job.isDone())
            return true;
        var resp = http.send(req, BodyHandlers.ofString());
        switch (resp.statusCode()) {
        case HTTP_NOT_FOUND:
            job.complete(new SimulationFailure(
                    job.input, false, "Deleted from server", resp.body()));
            return true;
        case HTTP_OK:
            var st = om.readValue(resp.body(), JobStatus.class);
            if (st.isActive()) {
                jobs.put(jobid, job);
                return false;
            }
            completeJob(jobid, st, job);
        default:
            throw new HttpException(resp.statusCode(), resp.body());    
        }
    }
    
    public static class TerminatedData {
        public int job;
        public JobStatus status;
    }

    public void on_terminated(Object... args) {
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
                completeJob(arg.job, arg.status, job);
            } catch (InterruptedException e) {
                error_jobs.put(arg.job, job);
                Thread.currentThread().interrupt();
                logger.error(
                        "on_terminated: interrupted on job " + arg.job, e);
            } catch (IOException e) {
                error_jobs.put(arg.job, job);
                logger.error(
                        "on_terminated: IO exception on job " + arg.job, e);
            }
        }
    }
    
    public IntensRunner(IntensModel model) {
        this.model = model;
        om = model.getSimulatorManager().protocolOM;
        http = HttpClient.newBuilder().build();
        sio = IO.socket(model.uri);
        sio.on("terminated", this::on_terminated);
        sio.connect();
    }

    public synchronized void close() throws IOException {
        if (sio.connected()) {
            sio.close();
        }
        if (!jobs.isEmpty()) {
            logger.warn("Closing runner with " + jobs.size() + " active jobs");
        }
    }

    public IntensJob start(SimulationInput input) throws IOException {
        // TODO Auto-generated method stub
        return null;
    }
}
