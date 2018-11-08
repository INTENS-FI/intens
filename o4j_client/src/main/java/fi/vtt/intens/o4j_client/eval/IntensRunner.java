package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.net.URI;
import static java.net.HttpURLConnection.*;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpResponse.BodyHandlers;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
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
     * Attempt to parse a HTTP response as a sim-eval type.
     * resp is in JSON, thus the parsers of sim-eval are of limited use.
     */
    private Object parseResult(Type typ, HttpResponse<String> resp)
            throws IOException {
        if (resp.statusCode() != HTTP_OK)
            throw new HttpException(resp.statusCode(), resp.body());
        switch(typ) {
        case DOUBLE:
        case TIMESTAMP:
            return om.readValue(resp.body(), Double.class);
        case INTEGER:
            return om.readValue(resp.body(), Integer.class);
        case STRING:
            return om.readValue(resp.body(), String.class);
        case LIST_OF_DOUBLE:
        case LIST_OF_INTEGER:
        case LIST_OF_TIMESTAMP:
            @SuppressWarnings("unchecked")
            List<Object> val = om.readValue(resp.body(), List.class);
            if (!typ.isCompatible(val))
                throw new IOException("Incompatible list for " + typ);
            return val;
        default:
            throw new IOException("Unsupported type " + typ);
        }
    }
    
    private synchronized IOException putResult(
            SimulationResults res, String comp, String op, Type typ,
            HttpResponse<String> resp) {
        try {
            res.put(comp, op, parseResult(typ, resp));
            return null;
        } catch (IOException e) {
            logger.error("putResult failed for " + comp + "." + op, e);
            return e;
        }
    }
    
    private void getResults(int jobid, IntensJob job)
            throws IOException, InterruptedException {
        var res_uri = model.uri.resolve("jobs/" + jobid + "/results/");
        var res = new SimulationResults(job.input, getLog(jobid));
        var ns = job.input.getNamespace();
        CompletableFuture<IOException>
            jobs = CompletableFuture.completedFuture(null);
        for (var comp_kv : ns.components.entrySet()) {
            for (var out_kv : comp_kv.getValue().outputs.entrySet()) {
                var req = HttpRequest.newBuilder(res_uri.resolve(
                        String.join(".", comp_kv.getKey(), out_kv.getKey())))
                        .build();
                jobs = http.sendAsync(req, BodyHandlers.ofString())
                        .thenApply(resp -> putResult(
                                res, comp_kv.getKey(), out_kv.getKey(),
                                out_kv.getValue(), resp))
                        .thenCombine(jobs, (e2, e1) -> e1 != null ? e1 : e2);
            }
        }
        IOException e = jobs.join();
        if (e != null)
            throw e;
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
            switch (st) {
            case DONE:
                getResults(jobid, job);
                return true;
            case FAILED:
                getError(jobid, job);
                return true;
            case CANCELLED:
                job.set_cancelled();
                return true;
            default:
                job.complete(new SimulationFailure(
                        job.input, false,
                        "Abnormal job status " + st, getLog(jobid)));
                return true;
            }
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
                switch (arg.status) {
                case DONE:
                    getResults(arg.job, job);
                    break;
                case FAILED:
                    getError(arg.job, job);
                    break;
                case CANCELLED:
                    job.set_cancelled();
                    break;
                default:
                    getJobStatus(arg.job, job);
                }
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
