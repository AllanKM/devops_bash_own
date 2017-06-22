
#*******************************************************************************************************
# tip_was_securityConfig_v3.py -  based on was_securityConfig
#   Author: James Walton
#   Initial Date: 08/27/2008
#
#   Change History: 
#   Lou Amodeo 03-01-2013  Add support for Websphere 8.5 
#   Gene Coley 04-10-2013  Add support for TIPprofile
#                          Supports ED only as of now
#              04-16-2013  Set RunAs user and group 
#              04-16-2013  Update the ldap group configuration to allow group name searches   
#              06-11-2013  V2 - Support EI's LDAP as well as bluepages.  
#                               If NCO, no ldap or WAS roles configured    
#              08-10-2013  Fix minor bugs.  Note a major fix has been added to the tad4d version that
#                          connects to the bluepages LDAP.   
#              06-08-2014  v3 1.05 Support profile JazzSMProfile used in TCR 3.1  
#    TODO:
#    1. Fix (enableWI) logic if used to support non-TIP or WI environments
#
#    NCO config - set RunAs user and group to netcool, itmusers
#    The LDAP config is still limited to TIPProfile.
#@  
#********************************************************************************************************
import sys
import os
import traceback
from java.lang import System

global AdminConfig
global AdminControl
True = 1
False = 0
script_version = '1.05a' 

adminRoles    = 'administrator adminsecuritymanager iscadmins'
operatorRoles = 'operator'
node          =  'TIPNode'

#*******************************************************************************************************
# Procedures
#*******************************************************************************************************
# TODO - update this usage doc 
def usage():
	print 'Usage:'
	print 'The EI user for WI ED are pre-filled by the script currently.'
	print '\nConfig Global Security with LDAP registry(bluepages) in federated config with TIPProfile'
	print '   wsadmin -lang jython -f tip_securityConfig_v3.py -ED -ldappassword <ldapPassword> -bindpassword <bindPassword> '	
	print '           -standalone  -keypassword <keyPassword>  [-bypasssave]  -tipid <tipid> [-debug]'
	
def getSecurityAdminMbean():
        try: result = AdminControl.queryNames('WebSphere:type=SecurityAdmin,*').split('\n')
        except:
                print 'AdminControl.queryNames(\'WebSphere:type=SecurityAdmin,*\') caught an exception:',sys.exc_info()
                return 
        if (result != []):
               	# incase more than one, just get the first one
                secMbean = result[0]
                return secMbean
        else:
                print 'Security Mbean was not found\n'
                return 

def disableLTPAKeyAutoGen():
  cellKSG=AdminConfig.getid('/KeySetGroup:CellLTPAKeySetGroup/')
  try: AdminConfig.modify(cellKSG,[['autoGenerate', 'false']])
  except:
    print 'AdminConfig.modify('+cellKSG+'[[\'autoGenerate\', \'false\']]) caught an exception:',sys.exc_info()
    sys.exit()

def disableLTPAKeyAutoGenSA():
	cellKSG=AdminConfig.getid('/KeySetGroup:NodeLTPAKeySetGroup/')
	try: AdminConfig.modify(cellKSG,[['autoGenerate', 'false']])
	except:
		print 'AdminConfig.modify('+cellKSG+'[[\'autoGenerate\', \'false\']]) caught an exception:',sys.exc_info()
		sys.exit()

# The roleObj is the group name
def addToAdminRole(roleType, roleObj):
        # Moved adminRoles = 'administrator adminsecuritymanager iscadmins'
        authTable = AdminConfig.getid('/AuthorizationTableExt:admin-authz.xml/')
        authz = AdminConfig.showAttribute(authTable, 'authorizations').split(']')[0].split('[')[1].split(' ')
        #Cycle through all admin roles, add user/group object to the administrator-type roles as defined above
        for a in authz:
                aRole = AdminConfig.showAttribute(a, 'role')
                rName = AdminConfig.showAttribute(aRole, 'roleName')
                if (adminRoles.find(rName) >= 0):
                        args = [['name', roleObj]]
                        try: AdminConfig.create(roleType, a, args)
                        except: print '### Error adding '+roleType+' '+roleObj+' to admin role '+rName+':',sys.exc_info()

def addToOpRole(roleType, roleObj):
        # adminRoles = 'operator'
        authTable = AdminConfig.getid('/AuthorizationTableExt:admin-authz.xml/')
        authz = AdminConfig.showAttribute(authTable, 'authorizations').split(']')[0].split('[')[1].split(' ')
        #Cycle through all config and op roles, add user/group object to the roles as defined above
        for a in authz:
                aRole = AdminConfig.showAttribute(a, 'role')
                rName = AdminConfig.showAttribute(aRole, 'roleName')
                # if (adminRoles.find(rName) >= 0):
                if (operatorRoles.find(rName) >= 0):
                        args = [['name', roleObj]]
                        try: AdminConfig.create(roleType, a, args)
                        except: print '### Error adding '+roleType+' '+roleObj+' to admin role '+rName+':',sys.exc_info()

def addAdminGroup(group):
        # cleanup first in case this is a rerun 
        print 'Cleanup admins in group %s'  % group
        removeGroupFromAdminRoles(group, adminRoles)
        roleType = 'GroupExt'
        print 'Add to admin role type %s group %s'  % (roleType, group)
        addToAdminRole(roleType, group)

def addOpGroup(group):
        # cleanup first in case this is a rerun 
        print 'cleanup operators in group %s' %  group
        removeGroupFromAdminRoles(group, operatorRoles)
        roleType = 'GroupExt'
        print 'Add to op role group %s'  % (group)
        addToOpRole(roleType, group)

def addAdminUser(user):
        roleType = 'UserExt'
        print 'Add admin user %s'  % (user)
        addToAdminRole(roleType, user)

def removeGroupFromAdminRoles(groupId, roleNames):
    if ( debug ): print '  Executing removeGroupFromAdminRoles for group: %s: roles %s' % (groupId, roleNames) 
    roleNamesList = roleNames.split()
    for role in roleNamesList:
       done = False 
       while ( done != True ):
         #if ( debug ): print 'Removing %s from %s' % (groupId, str(role))
         arg = '[-groupids [%s] -roleName %s]'  % (groupId, role)
         try:   AdminTask.removeGroupsFromAdminRole(arg)
         except: 
             done = True
             pass              
    if ( debug ): print '  Executing removeGroupFromAdminRoles for group: %s...completed'  % groupId
  
# Probably can be obtained from AdminTask 
# If profile is TIPProfile the calling script runs wsadmin from the profile's bin directory
# so using user_install_root works
def get_profile_name():
    user_install_root = System.getProperty("user.install.root")
    return os.path.basename(user_install_root)

# Convert a string representation of a list to a real list
def stringlist_to_list(s):
    if ( s.endswith('] ]') ):  ks = s[2:-3]    # remove leading and trailing brackets
    else:  ks =  ks[2:-2]         
    ks2 = ks1.split("] [")
    return ks2
 
# test to determine text for 'adding' or 'updating' 
def get_text(exists):
    if ( exists ) : return "Updating "
    else: return "Adding "

def text_contains(string, arg):
     if ( string.find(arg) > 0 ): return True
     else: return False         

# This supports LDAP config to bluepages running TIP
def retrieve_signer_certificate():
    exists = False
    rtn = True
    status = "successful"
    retrieve_successful = False
    signer_certificate =''
    getSignerCertificate_args   = '[ -certificateAlias LDAP10  \
                                     -keyStoreName NodeDefaultTrustStore \
                                     -keyStoreScope (cell):TIPCell:(node):TIPNode ]'
    retrieveSignerFromPort_args = '[ -certificateAlias LDAP10  \
                                     -keyStoreName NodeDefaultTrustStore \
                                     -keyStoreScope  (cell):TIPCell:(node):TIPNode \
                                     -host bluepages.ibm.com \
                                     -port 636 \
                                     -sslConfigName NodeDefaultSSLSettings \
                                     -sslConfigScopeName (cell):TIPCell:(node):TIPNode ]'
    listSignerCertificates_args = '[-keyStoreName NodeDefaultTrustStore \
                                    -keyStoreScope (cell):TIPCell:(node):TIPNode ]' 
    getKeyStoreInfo_args        = '[-keyStoreName  NodeDefaultTrustStore  \
                                    -scopeName (cell):TIPCell:(node):TIPNode ]'
    modify_args           = '[-keyStoreName NodeDefaultTrustStore  \
                              -keyStorePassword ' + keyPassword + ' \
                              -scopeName (cell):TIPCell:(node):TIPNode '    
    modify_writable_args  = modify_args + ' -keyStoreReadOnly false ]'  
    modify_readonly_args  = modify_args + ' -keyStoreReadOnly true ]'   
                                                      
    print 'Locate signer certificate with alias LDAP10 from our store'
    if (debug):
        print 'modify_writable_args=',modify_writable_args
        print 'modify_readonly_args=',modify_readonly_args    
    try:
        signer_certificate = AdminTask.getSignerCertificate(getSignerCertificate_args)
        print '  located..'
        print '  Current signer certificate:\n',signer_certificate 
        exists = True
    except:
        # this works to confirm:
        #     ex = sys.exc_info() 
        #     print ' exception: ' + str(ex)
        #     if text_contains(str(ex),'Signer certificate alias \"LDAP10\" does not exist'):
        #         exists = 0
        #     else: do-what  
        pass
    
    # If the signer cert does not exist under alias LDAP10, issue the retrieve    
    if not ( exists ):
        print '  not located under that alias, so issuing retrieve certificate'
        try:
            # Notes - 1. the certificate could exist under a different alias
            #         2. the keystore must not be read-only 
            chged_to_rw = False
            # 1. If the keystore is read only, make it readable  
            ksinfo = AdminTask.getKeyStoreInfo(getKeyStoreInfo_args)
            if text_contains(ksinfo, 'readOnly true'):
                 chged_to_rw = True
                 print '    modifying keystore to make writeable'
                 try:    
                    AdminTask.modifyKeyStore(modify_writable_args)
                    ksinfo = AdminTask.getKeyStoreInfo(getKeyStoreInfo_args)
                    # This can create a list:  stringlist_to_list(ksinfo) 
                    if text_contains(ksinfo, 'readOnly false'):
                        print '    modifying keystore to make writeable..successful'      
                 except: print '     modifing keystore failed\n',sys.exc_info()       
            
            # 2. Retrieve signer certificate           
            AdminTask.retrieveSignerFromPort(retrieveSignerFromPort_args)
            retrieve_successful = True
            print '    retrieve executed successfully'
            
            # 3. Mofify keystore to be read only if that's how we started out
            if ( chged_to_rw ):
                print '    modifying keystore to be read-only'
                try:    AdminTask.modifyKeyStore(modify_readonly_args)   
                except: print '     modify failed\n',sys.exc_info()     
           
            # Confirm 
            try:
                signer_list = AdminTask.listSignerCertificates(listSignerCertificates_args)
                print "  Signer certificates after retrieve cert\n %s\n" % signer_list
                #     AdminTask.getSignerCertificate(getSignerCertificate_args)
            except: 
                print '  Unable to list the signer certs',sys.exc_info()  
            try:       
                print '  saving the wsadmin configuration for the signer certificate..........'
                AdminConfig.save()
                print '  saving the wsadmin configuration..complete ..........................'
            except:
                print '**ERROR**Unable to retrieve and store the bluepages certificate'
                print '         We cannot continue' 
                raise     
            
        except:
            ex = sys.exc_info()  
            if text_contains(str(ex), 'already exists in key store'):
                # This condition considered a successful retrieve 
                print '    Certificate already exists in key store, likely under a different alias'
            else:  
               print '    **ERROR** retrieve failed - see exception messages - not safe to continue\n'
               print '    **Terminating configuration**\n', sys.exc_info() 
               raise
    
    if ( rtn == False ): status = "not successful"
    print 'Locate signer certificate with alias LDAP10...%s\n' % status
    return rtn 

#-----------------------------------------------------------------------------------------------------------
# Configure the standard bluepages.ibm.com ldap. 
# Need to have or retrieve the signer certificate and save the config before we update or add this ldap.
# Since we need to save the config, do the signer certificate work first  
#-------------------------------------------------------------------------------------------------------------              
def configLDAP():  
   
    certificate_loaded = False 
    print
    print 'Configuring EI security for WAS Tivoli Integrated Portal profile \n'
    try:
      
      # 0. Load the ldap's signer certificate and save config    
      certificate_loaded = retrieve_signer_certificate()
      if not certificate_loaded :
          print '--------------------------------------------------------------'
          print 'WARNING: The bluepages signer certificate may not be retrieved'
          print '         If not, this configuration will fail'
          print '--------------------------------------------------------------'    
      
      # 1 Start the process of configuring the WIM user registry  
      AdminTask.configureAdminWIMUserRegistry('[-realmName defaultWIMFileBasedRealm -verifyRegistry false ]')
         
      # 2 Create or update the wsadmin LDAP repository for our bluepages ldap
      #   in the IdMgrRepositories  
      exists = 0
      idMgrRepos = AdminTask.listIdMgrRepositories()
      print 'Initial existing IdMgrRepositories: \n%s' % idMgrRepos 
      print
      if text_contains(idMgrRepos, 'LDAP10={'): 
         exists = 1   
    
      IdMgrLDAPRepository_args = '[-id LDAP10 -adapterClassName com.ibm.ws.wim.adapter.ldap.LdapAdapter \
                                   -ldapServerType CUSTOM -sslConfiguration -certificateMapMode exactdn \
                                   -supportChangeLog none -certificateFilter -loginProperties mail ]'
      print get_text(exists) + 'IdMgrLDAPRepository LDAP10'  
      # The update method tries to communicate with the ldap host. 
      # The signer cert must have been retrieved and config saved. 
      if ( exists ): 
          AdminTask.updateIdMgrLDAPRepository(IdMgrLDAPRepository_args)
      else:
          AdminTask.createIdMgrLDAPRepository('-default true ' + IdMgrLDAPRepository_args)
      print get_text(exists) + 'IdMgrLDAPRepository LDAP10...complete'  
      idMgrRepos = AdminTask.listIdMgrRepositories()   
      print 'Updated IdMgrRepositories: \n%s\n' % idMgrRepos 
                       
      # 3  Add our bluepages LDAP server to our bluepages IdMgr repository 
      #    Update if this is a config rerun 
      exists = 0
      try:
          AdminTask.getIdMgrLDAPServer('[-id LDAP10 -host bluepages.ibm.com ]') 
          exists = 1
      except:
          # Our server has not been configured
          pass
      IdMgrLDAPServer_args = '-id LDAP10 -host bluepages.ibm.com -port 636  -referal ignore -sslEnabled true \
                    -ldapServerType CUSTOM -sslConfiguration -certificateMapMode exactdn \
                    -certificateFilter -authentication simple'
      ### needs -bindDN  -bindPassword ********  
      
                    
      print get_text(exists) + 'LDAP10 with bluepages server'   
      if ( exists ): AdminTask.updateIdMgrLDAPServer(IdMgrLDAPServer_args)
      else:          AdminTask.addIdMgrLDAPServer   (IdMgrLDAPServer_args)
      # Capture the results
      IdMgrLDAP10_bluepages  = AdminTask.getIdMgrLDAPServer('[-id LDAP10 -host bluepages.ibm.com ]')
      print 'IdMgrLDAP10_bluepages: \n%s' % IdMgrLDAP10_bluepages   
      print get_text(exists) + 'LDAP10 with bLuepages server..complete'   
      
      # 4  Set the login properties for using the user's email address       
      IdMgrLDAPRepository_args = '[-id LDAP10  -adapterClassName com.ibm.ws.wim.adapter.ldap.LdapAdapter \
                                  -ldapServerType CUSTOM  -sslConfiguration -certificateMapMode exactdn \
                                  -certificateFilter -supportChangeLog none -loginProperties mail]'
      AdminTask.updateIdMgrLDAPRepository(IdMgrLDAPRepository_args)  
       
      # 5  Add or update the 'base entry' name for this LDAP in the federated repository     
      #    Two AdminTask's
      IdMgrRepositoryBaseEntry_arg = '[-id LDAP10  -name o=ibm.com -nameInRepository o=ibm.com]'  
      exists = 0
      IdMgrRepository_ldap10_baseentries = ""
      try:
          IdMgrRepository_ldap10_baseentries = AdminTask.listIdMgrRepositoryBaseEntries('[-id LDAP10]') 
          exists = 1
      except:
          pass 
      # 5.1
      print get_text(exists) + 'IdMgrRepositoryBaseEntry'
      if ( exists ): 
           print '  before IdMgrRepositoryBaseEntry: \n%s' % IdMgrRepository_ldap10_baseentries  
           AdminTask.updateIdMgrRepositoryBaseEntry(IdMgrRepositoryBaseEntry_arg)  
      else:
           AdminTask.addIdMgrRepositoryBaseEntry   (IdMgrRepositoryBaseEntry_arg)   
      IdMgrRepository_ldap10_baseentries = AdminTask.listIdMgrRepositoryBaseEntries('[-id LDAP10]')  
      print '  after IdMgrRepository_ldap10_baseentries: %s' % IdMgrRepository_ldap10_baseentries           
      print get_text(exists) + 'IdMgrRepositoryBaseEntry..complete'           
      
      # 5.2 Add the bluepages ldap base entry to the realm  
      #     Get the realm name from the configuration 
      #     The default name is defaultWIMFileBasedRealm, but it could have been changed  
      print 'Adding bluepages ldap base entry to the realm' 
      fed_repos_realm_name = AdminTask.getIdMgrDefaultRealm() 
      realm_name_arg = '[-name %s ]' %fed_repos_realm_name
      name_baseentry_arg = '[-name %s -baseEntry o=ibm.com]' % fed_repos_realm_name  
      print '  Located realm name: %s' % fed_repos_realm_name
      exists = 0
      realm_base_entries = ""
      # Cleanup what's there or the process will just add another entry 
      try:
          # Sample output from AdminTask.listIdMgrRealmBaseEntries
          #          'o=defaultWIMFileBasedRealm\no=ibm.com'
          realm_base_entries = AdminTask.listIdMgrRealmBaseEntries(realm_name_arg ) 
          # if text_contains(realm_base_entries, 'o=ibm.com'): exists = 1 
          if 'o=ibm.com' in realm_base_entries.split("\n"): 
              exists = 1  
      except:
          pass 
             
      # 5.3  Add our bluepages ldap to the realm if it's not there 
      while exists: 
          try:
              print '  Removing previous realm base entry for o=ibm.com'  
              AdminTask.deleteIdMgrRealmBaseEntry(name_baseentry_arg)
              realm_base_entries = AdminTask.listIdMgrRealmBaseEntries(realm_name_arg ) 
              if 'o=ibm.com' not in realm_base_entries.split("\n"): exists = 0  
          except: 
              print '   Unexpected error in AdminTask.deleteIdMgrRealmBaseEntry\n',sys.exc_info()
              exists = 0 
              pass    
      print '  Adding realm base entry for o=ibm.com'           
      AdminTask.addIdMgrRealmBaseEntry(name_baseentry_arg) 
      realm_base_entries = AdminTask.listIdMgrRealmBaseEntries(realm_name_arg ) 
      print '  Result realm base entries: \n%s' %realm_base_entries 
      print 'Adding bluepages ldap base entry to the realm...complete' 
      
      # 6  Validate the admin user - which remains in the fileRegistry repository, rather than in LDAP 
      print 'Validating administrator userid exists'   
      ans = AdminTask.validateAdminName('[-registryType WIMUserRegistry -adminUser tipadmin ]') 
      if ans == 'true': print '  user tipadmin exists in WIMUserRegistry'
      else:             print '  WARMING: user tipadmin does not exists in WIMUserRegistry'         
      print 'Validating administrator userid exists...complete' 
      
      # 7 Set the user search base
      print 'Configuring the bluepages ldap user configuration' 
      exists = 0
      IdMgrLDAPEntityType_person_args = '[-id LDAP10 -name PersonAccount -objectClasses ibmPerson;inetorgperson \
                                          -searchBases c=us,ou=bluepages,o=ibm.com -searchFilter ]'  
      try: 
          AdminTask.getIdMgrLDAPEntityType('[-id LDAP10 -name PersonAccount]')
          exists = 1
      except:
          pass    
      print get_text(exists) + 'IdMgrLDAPEntityType for person account' 
      if ( exists ): AdminTask.updateIdMgrLDAPEntityType(IdMgrLDAPEntityType_person_args)
      else:          AdminTask.addIdMgrLDAPEntityType   (IdMgrLDAPEntityType_person_args)    
      print get_text(exists) + 'IdMgrLDAPEntityType for person account..complete' 
      person_config = AdminTask.getIdMgrLDAPEntityType('[-id LDAP10 -name PersonAccount]')
      print 'LDAP10 PersonAccount properties: %s' % person_config
    
         
      # 8 Group search base
      
      # 8.1 Set the IdMgrLDAPEntityType for "Group"
      print 'Configuring the bluepages ldap group configuration' 
      exists = 0
      IdMgrLDAPEntityType_group_args = '[-id LDAP10 -name Group -objectClasses groupOfUniqueNames  \
                                         -searchBases ou=memberlist,ou=ibmgroups,o=ibm.com -searchFilter ]'
      try:
          AdminTask.getIdMgrLDAPEntityType('[-id LDAP10 -name Group]') 
          exists = 1 
      except:
          pass     
      print get_text(exists) + 'IdMgrLDAPEntityType for group'     
      if ( exists ): AdminTask.updateIdMgrLDAPEntityType(IdMgrLDAPEntityType_group_args) 
      else:          AdminTask.addIdMgrLDAPEntityType   (IdMgrLDAPEntityType_group_args)       
      group_config = AdminTask.getIdMgrLDAPEntityType('[-id LDAP10 -name Group]') 
      print get_text(exists) + 'IdMgrLDAPEntityType for group...complete'    
      print 'ldap group account properties: %s ' % str(group_config)     
    
      # 8.2 Set the IdMgrLDAPGroupConfig and add the group attributes needed (for an ldap in a federated repository)
      #     If a group config exists for our ldap, delete it, which also deletes any attached attributes   
       
      group_config = AdminTask.getIdMgrLDAPGroupConfig('[-id LDAP10 ]') 
      if len(group_config) > 0:
          print '  Deleting the existing ldap group config: %s' % group_config
          AdminTask.deleteIdMgrLDAPGroupConfig('[-id LDAP10 ]')   
      AdminTask.setIdMgrLDAPGroupConfig    ('[-id LDAP10 -name uniqueMember -scope all]') 
      AdminTask.addIdMgrLDAPGroupMemberAttr('[-id LDAP10 -name uniqueMember -objectClass groupOfUniqueNames -scope all]')
      print '  LDAP10 group updated config: %s' % AdminTask.getIdMgrLDAPGroupConfig('[-id LDAP10 ]') 
      print '               attributes: %s' % AdminTask.getIdMgrLDAPGroupMemberAttrs('[-id LDAP10]')  
            
      # 9 Allow tipadmin and other admin users in defaultWIMFileBasedRealm to logon if ldap access id down 
      updIdMgrRealm_arg = '-name %s -allowOperationIfReposDown true' % fed_repos_realm_name
      AdminTask.updateIdMgrRealm(updIdMgrRealm_arg)          
       
      # 10 Summary of the federated repository work 
      #   List the repositories (again), base entry for the newly added/updated repository, and others 
      repos_list = AdminTask.listIdMgrRepositories()
      print
      print '**Summary**'
      print 'Repositories: \n%s' %repos_list
      base_entries_list = AdminTask.listIdMgrRepositoryBaseEntries('[-id LDAP10]')
      print 'Base entry for LDAP10: %s' %  base_entries_list 
      print 'IdMgrLDAP10_bluepages: \n%s' % IdMgrLDAP10_bluepages
      #print 'IdMgrRepository_ldap10_baseentries: \n%s' % IdMgrRepository_ldap10_baseentries
      print 'Realm_base_entries: \n%s' % realm_base_entries  
      print 'user person config: \n%s:'% person_config 
      print 'Group config: \n%s'       % group_config 
                
      # TIPProfile should already be configured this way 
      print
      print 'Updating global security attributes'
      AdminTask.setGlobalSecurity('[-enabled true]')  # this one ?
      AdminTask.setAdminActiveSecuritySettings('[-activeUserRegistry WIMUserRegistry  -enableGlobalSecurity true]')
      AdminTask.setAdminActiveSecuritySettings('[-appSecurityEnabled true]')
      AdminTask.setAdminActiveSecuritySettings('[-enforceJava2Security false]')
      print 'Updating global security attributes...complete'
      print
      
      # Config Run As  - moved !
      #run_user = 'webinst'
      #run_group = 'mqm' 
      #print "Setting RunAs user: %s and group: %s " %(run_user, run_group) 
      #s1 = AdminConfig.getid('/Cell:TIPCell/Node:TIPNode/Server:server1/')
      #pd =  AdminConfig.showAttribute(s1, 'processDefinitions').split('[')[1].split(']')[0].split()[0] 
      #pexec = AdminConfig.showAttribute(pd,'execution')     
      #exec_attr = []
      #exec_attr.append(['runAsUser',  run_user  ]); 
      #exec_attr.append(['runAsGroup', run_group ])
      #AdminConfig.modify(pexec, exec_attr)   
      #exec_report = AdminConfig.showall(pexec)[1:][:-1].split(']\n[')
      #print '  Process execution attributes:\n %s' % exec_report
      #print 'Setting RunAs user/group...completed'
      
      # Config admin roles -  moved  
      #print 'Setting up Admin Roles for ITCS104'
      #addAdminGroup('ei_ed_wasadmins')
      #addOpGroup('ei_webmasters')
      #print 'Setting up Admin Roles for ITCS104...complete'
    
      print 'Configuring Tivoli Integrated Portal profile...complete' 
    
    except:
       print '**ERROR configuring TIPProfile for security: ',sys.exc_info()
       _type, _val, _tb = sys.exc_info()
       traceback.print_exception(_type,_val,_tb)
       sys.exit()

def configTAD():
   print 'Configuring TAD4D TIP security' 
   configLDAP()     
   configRunAs('webinst', 'mqm') 
   print 'No admin roles configured'  
   # Config admin roles 
   print 'Setting up Admin Roles for ITCS104'
   addAdminGroup('ei_ed_wasadmins')
   addOpGroup('ei_webmasters')
   print 'Setting up Admin Roles for ITCS104...complete'

     
   print 'Configuring TAD4D TIP security...complete'    
   
def configNCO():
   print 'Configuring NCO TIP security'      
   configRunAs('netcool', 'itmusers') 
   print 'No admin roles configured'    
   print 'Configuring NCO TIP security...complete'    
   
def configTCR():
   print 'Configuring TCR security'  
   print '** Bypassing config of EI LDAP.. must do manually for now using TCR EI doc**'    
   configRunAs('webinst', 'itmusers') 
   print 'Configuring admin roles using eiadm'
   addAdminGroup('eiadm')
   addOpGroup('eiadm')  
   print 'Configuring TCR TIP security...complete'    

# Same role as previously configured for TCR   
def configTCR31():
   print 'Configuring TCR31 security'  
   print '** Bypassing config of EI LDAP.. must do manually ...TCR3.1 EI doc is available**'    
   configRunAs('webinst', 'mqm') 
   print 'Configuring admin roles using eiadm'
   addAdminGroup('eiadm')
   addOpGroup('eiadm')  
   print 'Configuring TCR31 security...complete'    
   
   
# Configure RunAs  
def configRunAs(user, group):    
   try:
      run_user = user
      run_group = group 
      print "Setting RunAs user: %s and group: %s " %(run_user, run_group) 
      
      if ( profile == 'JazzSMProfile' ):
        	s1 = AdminConfig.getid('/Cell:JazzSMNode01Cell/Node:JazzSMNode01/Server:server1/')
      else:
          s1 = AdminConfig.getid('/Cell:TIPCell/Node:TIPNode/Server:server1/')
          
      pd = AdminConfig.showAttribute(s1, 'processDefinitions').split('[')[1].split(']')[0].split()[0] 
      pexec = AdminConfig.showAttribute(pd,'execution')     
      exec_attr = []
      exec_attr.append(['runAsUser',  run_user  ]) 
      exec_attr.append(['runAsGroup', run_group ])
      AdminConfig.modify(pexec, exec_attr)   
      exec_report = AdminConfig.showall(pexec)[1:][:-1].split(']\n[')
      print '  Process execution attributes:\n %s' % exec_report
      print 'Setting RunAs user/group...complete'
   except:
      print '**ERROR configuring RunAs: ',sys.exc_info()
      _type, _val, _tb = sys.exc_info()
      traceback.print_exception(_type,_val,_tb)
      sys.exit() 

print  
print "Executing tip_was_securityConfig_v3.py version %s" %str(script_version) 
#*******************************************************************************************************
# Commandline parameter handling
#*******************************************************************************************************
argerr   = 0
enableWI = 0
enableUD = 0
enableED = 0
standAlone = 0
bypassSave = 0
debug    = 0
ldapType = 'blue'  # blue | ei | none
tipID    = 'TAD'   # TAD, NCO, TCR,TCR31   

tad4d    = 0       # If set, also configure for TAD4D requirements
#                  # Not used yet  

# enableWI not supported
# -bindpassword is for ldap in ldap's where bind pw is needed
# The other passwords are not used here 
i = 0
argc=len(sys.argv)
while (i < argc):
        arg = sys.argv[i]
        if (arg == '-WI'): enableWI = 1
        elif (arg == '-ED' or arg == '-BP'): enableED = 1
        elif (arg == '-ldappassword'):
                i += 1
                if (i < argc): ldapPassword = sys.argv[i]
                else: argerr = 1
        elif (arg == '-bindpassword'):
                i += 1
                if (i < argc): bindPassword = sys.argv[i]
                else: argerr = 2  
        elif (arg == '-keypassword'):
                i += 1
                if (i < argc): keyPassword = sys.argv[i]
                else: argerr = 8    
        elif (arg == '-ldap'):
                i += 1
                if (i < argc): ldapType = sys.argv[i]
                else: argerr = 9         
        elif (arg == '-tipid'):
                i += 1
                if (i < argc): tipID = sys.argv[i]
                else: argerr = 10         
        elif (arg == '-standalone'): standAlone = 1
        elif (arg == '-tad4d'): tad4d = 1
        elif (arg == '-bypasssave'): bypassSave = 1
        elif (arg == '-debug'): debug = 1
        else:
            print "Invalid argument",arg 
            argerr = 3  
        i += 1
        
ldapPwdExists = ('ldapPassword' in locals().keys() or 'ldapPassword' in globals().keys())
bindPwdExists = ('bindPassword' in locals().keys() or 'bindPassword' in globals().keys())
keyPwdExists  = ('keyPassword'  in locals().keys() or 'keyPassword'  in globals().keys())
enableCount = enableWI + enableED
# if (not ldapPwdExists and enableWI == 0 and enableED == 0): argerr = 4
# if (not ldapPwdExists and enableWI == 1 and enableUD == 1): argerr = 5
# if (not bindPwdExists and enableWI == 1): argerr = 6
if (enableCount != 1): argerr = 7    
if (argerr):
        print '### Invalid command line invocation (reason code '+str(argerr)+').'
        usage()
        sys.exit(1)
print 
print "enableWI: %s" %str(enableWI) 
print "enableED: %s" %str(enableED) 
#print "LDAP type: %s" %str(ldapType)
print "TIP ID:   %s" %str(tipID)
if ( tipID != 'TAD' ):
  print "tad4d:    %s" %str(tad4d)

#*******************************************************************************************************
# Decipher and Perform Requested Action
#*******************************************************************************************************
if (standAlone): dmgr = AdminControl.completeObjectName('name=server1,type=Server,*')
else: dmgr = AdminControl.completeObjectName('name=dmgr,type=Server,*')

fullVersion = AdminControl.getAttribute(dmgr, 'platformVersion')
print 'fullVersion = ',fullVersion
version = fullVersion[0:3]
print 'version = ',version

# If TIPProfile, call approproprate method   
profile = get_profile_name()
print 'profile = ',profile
if ( profile == 'TIPProfile' ):
    if not keyPwdExists:
        argerr = 8
        print '### Invalid command line invocation (reason code '+str(argerr)+').'
        print '### Argument -keypassword required to configure TIPProfile' 
        usage()
        sys.exit()
    if tipID == 'NCO':
        configNCO()   # Config the NCO version of the TIP   
    elif tipID == 'TCR':
        configTCR()
    else:
        configTIP()   # Config the TAD blue pages   

# for TCR 3.1
elif ( profile == 'JazzSMProfile' ):
    configTCR31()	    # Config TCR 3.1 

else:
  # Not **TIPProfile or JazzSMProfile**     
  # Grab LDAP object, set common Registry values
  ldap = AdminConfig.getid('/LDAPUserRegistry:/')
  try: AdminConfig.modify(ldap, [['reuseConnection', 'false'], ['sslEnabled', 'true'], ['type', 'CUSTOM']])
  except:
         print '### Error updating common LDAP Registry values:',sys.exc_info()
         sys.exit()

  # enableWI not yet supported 
    
  # enableED
  print 'enableED processing\n'       
  # result = AdminConfig.modify(ldap, [['baseDN', 'o=ibm.com'], ['primaryAdminId', 'C-BCYD897@nomail.relay.ibm.com'], ['useRegistryServerId', 'false'], ['realm', 'bluepages.ibm.com:636']])
  result = AdminConfig.modify(ldap, [['baseDN', 'o=ibm.com'], ['primaryAdminId', 'tipadmin'], ['useRegistryServerId', 'false'], ['realm', 'bluepages.ibm.com:636']])
        
  if (result != ''):
          print '### Error updating ED LDAP values\n'+result
          sys.exit()
  #Just grab the first ldap host in the list, there should not be more than one.
  ldaphosts = AdminConfig.showAttribute(ldap, 'hosts').split('[')[1].split(']')[0].split()[0]
     
  print 'ldaphosts \n' + str(ldaphosts)
       
  try: AdminConfig.modify(ldaphosts, [['host', 'bluepages.ibm.com'], ['port', '636']])
  except:
          print '### Error updating ED LDAP host and port:',sys.exc_info()
          sys.exit()
  ldapfilter = AdminConfig.showAttribute(ldap, 'searchFilter')
  result = AdminConfig.modify(ldapfilter, [['groupFilter', '(&(cn=%v)(objectclass=groupOfUniqueNames))' ], ['groupIdMap', '*:cn'], ['groupMemberIdMap', 'groupOfUniqueNames:uniqueMember'], ['userFilter', '(&(mail=%v)(objectclass=ePerson))' ], ['userIdMap', '*:uid']])
  if (result != ''):
          print '### Error updating ED LDAP filter values:',sys.exc_info()
          sys.exit()
      
  #Setup Admin Roles for users/groups - ITCS104 required
  addAdminGroup('ei_ed_wasadmins')
  addOpGroup('ei_webmasters')

  print 'Enable global security\n' 

  #Enabled Global Security with the newly configured registry
  security = AdminConfig.list('Security')
  sec_attrib = []
  sec_attrib.append(['activeUserRegistry', ldap])        
  sec_attrib.append(['enforceJava2Security', 'false'])
  sec_attrib.append(['appEnabled', 'true'])
  sec_attrib.append(['enabled', 'true'])
  try: AdminConfig.modify(security, sec_attrib)
  except:
        print 
        print '### Error updating common Security attributes:',sys.exc_info()
        print 
        _type, _val, _tb = sys.exc_info()
        traceback.print_exception(_type,_val,_tb)
        sys.exit()

#
# End of profile-specific work 
#

# Turn off autoGen of the LTPA keys
print 'Disabling Auto-Generation of LTPA KeySetGroup'
if (standAlone): disableLTPAKeyAutoGenSA()
else: disableLTPAKeyAutoGen()
print 'Disabling Auto-Generation of LTPA KeySetGroup..successful'

#
# Save
#
if not bypassSave:
    print 'Saving configuration...\n'
    AdminConfig.save()
    if  profile == 'TIPProfile' or profile == 'JazzSMProfile' :
        print '\nNode sync not applicable with this profile.\n'	
    else:	
        print '\nYou must synchronize your changes across the cell to update any federated nodes.\n'
        print '!! More importantly the dmgr and any federated nodes (nodeagents/appservers) must be restarted. !!\n'
    print 'Saving configuration...complete. \n'
else: 
    print '\nSaving configuration bypassed by request\n'    

