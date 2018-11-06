package fi.vtt.intens.o4j_client.eval;

import java.util.concurrent.CompletableFuture;

import eu.cityopt.sim.eval.SimulationOutput;

public class IntensJob extends CompletableFuture<SimulationOutput>  {

    @Override
    public boolean cancel(boolean mayInterruptIfRunning) {
        //TODO If we add a cancellation REST API, use it here.
        return super.cancel(mayInterruptIfRunning);
    }
}
