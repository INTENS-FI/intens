package fi.vtt.intens.o4j_client.eval;

import java.util.concurrent.CompletableFuture;

import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationOutput;

public class IntensJob extends CompletableFuture<SimulationOutput>  {
    public final SimulationInput input;

    public IntensJob(SimulationInput input) {
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
     * @return whether we were able to cancel the job
     *   (false if it had already completed).
     */
    public boolean set_cancelled() {
        // TODO Auto-generated method stub
        return super.cancel(false);
    }
}
