package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.InputStream;

import javax.inject.Inject;
import javax.inject.Singleton;

import eu.cityopt.opt.ga.ModelFactory;
import eu.cityopt.sim.eval.ConfigurationException;
import eu.cityopt.sim.eval.SimulatorManagers;

@Singleton
public class IntensFactory extends ModelFactory {
    public final static String name = "simsvc";
    public final IntensManager mgr;

    @Inject
    public IntensFactory(IntensManager mgr) {
        this.mgr = mgr;
        SimulatorManagers.register(name, mgr);
    }

    public IntensModel loadModel(InputStream in)
            throws IOException, ConfigurationException {
        return mgr.parseModel(name, in);
    }
}
