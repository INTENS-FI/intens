package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;

import javax.net.ssl.SSLSocket;

import com.fasterxml.jackson.annotation.JsonTypeName;

import okhttp3.Authenticator;
import okhttp3.Credentials;
import okhttp3.Interceptor;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.Route;

/**
 * Implements HTTP basic authentication for OkHttp3.
 * Based on an example in the library documentation.
 * Can also be used as an interceptor, which always adds the authentication
 * credentials instead of trying every request without and retrying
 * if the server responds with 401.
 */
@JsonTypeName("BasicAuth")
public class BasicAuthenticator implements Authenticator, Interceptor {
    public String username, password;

    public BasicAuthenticator() {}

    public BasicAuthenticator(String username, String password) {
        this.username = username;
        this.password = password;
    }

    /**
     * Add authentication credentials to req.
     * If req already has an Authorization header, return null.
     * Otherwise return a copy of req with an Authorization header
     * added (req is not modified).
     */
    public Request addAuth(Request req) {
        if (req.header("Authorization") != null)
            // Tried that, didn't work.
            return null;
        else
            return req.newBuilder().header(
                    "Authorization", Credentials.basic(username, password))
                    .build();
    }

    @Override
    public Request authenticate(Route route, Response response)
            throws IOException {
        return addAuth(response.request());
    }

    /**
     * Add authentication credentials to SSL requests.
     * If we have an SSL connection and there is no Authorization header
     * in the request, add one.  Otherwise process the request as is.
     * This should be used as a network interceptor because it needs access
     * to the connection.
     */
    @Override
    public Response intercept(Chain chain) throws IOException {
        var req = chain.request();
        var conn = chain.connection();
        if (conn != null && conn.socket() instanceof SSLSocket) {
            var areq = addAuth(req);
            if (areq != null)
                req = areq;
        }
        return chain.proceed(req);
    }
}
