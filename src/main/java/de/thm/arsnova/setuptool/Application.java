package de.thm.arsnova.setuptool;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import com.fourspaces.couchdb.Database;

@Component
public class Application {

	private Database database;
	
	private String databaseHost;
	private int databasePort;
	private String databaseName;
	
	@Value("${couchdb.host}")
	public final void setDatabaseHost(String databaseHost) {
		this.databaseHost = databaseHost;
	}
	
	@Value("${couchdb.port}")
	public final void setDatabasePort(String databasePort) {
		this.databasePort = Integer.parseInt(databasePort);
	}
	
	@Value("${couchdb.name}")
	public final void setDatabaseName(String databaseName) {
		this.databaseName = databaseName;
	}
	
	public static void main(String[] args) throws IOException {
		ApplicationContext context = new ClassPathXmlApplicationContext("application-context.xml");
		Application app = context.getBean(Application.class);
		
		app.startup();
	}
	
	public void startup() throws IOException {
		File viewDirectory = new ClassPathResource("views").getFile();
		if (viewDirectory.isDirectory()) {
			for (File viewFile : viewDirectory.listFiles()) {
				BufferedReader reader = new BufferedReader(new FileReader(viewFile));
				
				StringBuilder sb = new StringBuilder();
				String line;
				while( ( line = reader.readLine() ) != null ) {
					sb.append(line);
				}				
				reader.close();
				
				this.setupView(sb.toString());
			}
		}
	}

	private void setupView(String viewCode) {
		this.getDatabase();
	}
	
	private Database getDatabase() {
		if (database == null) {
			try {
				com.fourspaces.couchdb.Session session = new com.fourspaces.couchdb.Session(
						databaseHost,
						databasePort
					);
					
				database = session.getDatabase(databaseName);
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
		
		return database;
	}
	
}
