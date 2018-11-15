package fi.vtt.intens.o4j_client.opt;

import java.nio.file.Paths;

import org.opt4j.core.config.annotations.File;
import org.opt4j.core.config.annotations.Info;

import eu.cityopt.opt.ga.CityoptFileModule;
import eu.cityopt.opt.ga.ModelFactory;
import fi.vtt.intens.o4j_client.eval.IntensFactory;
import fi.vtt.intens.o4j_client.eval.IntensJacksonModule;

@Info("A Cityopt problem with evaluations on a pre-deployed simsvc server")
public class SimsvcModule extends CityoptFileModule {

    @Info("The model definition file")
    @File(".yaml")
    private String modelFile = "";
    
    @Override
    public void config() {
        super.config();
        install(new IntensJacksonModule());
        bind(ModelFactory.class).to(IntensFactory.class).in(SINGLETON);
        bindModelFile(Paths.get(modelFile));
    }
}
