package fi.vtt.intens.o4j_client.eval;

import java.util.concurrent.CompletableFuture;

import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationOutput;

public class IntensJob extends CompletableFuture<SimulationOutput>  {
    public final int jobid;
    public final SimulationInput input;

    public IntensJob(int jobid, SimulationInput input) {
        this.jobid = jobid;
        this.input = input;
    }

    @Override
    public boolean cancel(boolean mayInterruptIfRunning) {
        //TODO If we add a cancellation REST API, use it here.
        return false;
    }

    /**
     * Mark the job as cancelled.
     * To be called when the server informs us of cancellation.
     * @return whether we were able to cancel the future.
     *   (false if it had already completed).
     */
    public boolean set_cancelled() {
        return super.cancel(false);
    }
}
