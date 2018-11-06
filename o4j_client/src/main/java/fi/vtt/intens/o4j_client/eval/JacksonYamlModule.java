package fi.vtt.intens.o4j_client.eval;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.google.inject.AbstractModule;
import com.google.inject.Provides;
import com.google.inject.Singleton;
import com.google.inject.name.Named;

/**
 * Bindings for reading YAML with Jackson.
 */
public class JacksonYamlModule extends AbstractModule {
    @Provides
    @Named("intensModel")
    @Singleton
    public static ObjectMapper getIntensModelOM() {
        return new YAMLMapper().registerModule(new JavaTimeModule());
    }
}
