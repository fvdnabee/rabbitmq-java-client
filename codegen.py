##  The contents of this file are subject to the Mozilla Public License
##  Version 1.1 (the "License"); you may not use this file except in
##  compliance with the License. You may obtain a copy of the License
##  at http://www.mozilla.org/MPL/
##
##  Software distributed under the License is distributed on an "AS IS"
##  basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
##  the License for the specific language governing rights and
##  limitations under the License.
##
##  The Original Code is RabbitMQ.
##
##  The Initial Developer of the Original Code is VMware, Inc.
##  Copyright (c) 2007-2011 VMware, Inc.  All rights reserved.
##

from __future__ import nested_scopes
import re
import sys

sys.path.append("../rabbitmq-codegen")  # in case we're next to an experimental revision
sys.path.append("codegen")              # in case we're building from a distribution package

from amqp_codegen import *

class BogusDefaultValue(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def java_constant_name(c):
    return '_'.join(re.split('[- ]', c.upper()))

javaTypeMap = {
    'octet': 'int',
    'shortstr': 'String',
    'longstr': 'LongString',
    'short': 'int',
    'long': 'int',
    'longlong': 'long',
    'bit': 'boolean',
    'table': 'Map<String,Object>',
    'timestamp': 'Date'
    }

javaTypesToCheckForNull = set([
    'String',
    'LongString',
    'Date'
    ])

javaPropertyTypeMap = {
    'octet': 'Integer',
    'shortstr': 'String',
    'longstr': 'LongString',
    'short': 'Integer',
    'long': 'Integer',
    'longlong': 'Long',
    'bit': 'Boolean',
    'table': 'Map<String,Object>',
    'timestamp': 'Date'
    }

def java_type(spec, domain):
    return javaTypeMap[spec.resolveDomain(domain)]

def java_name(upper, name):
    out = ''
    for c in name:
        if not c.isalnum():
            upper = True
        elif upper:
            out += c.upper()
            upper = False
        else:
            out += c
    return out

def java_class_name(name):
    return java_name(True, name)

def java_getter_name(name):
    return java_name(False, 'get-' + name)

def java_property_type(spec, type):
    return javaPropertyTypeMap[spec.resolveDomain(type)]
def java_field_name(name):
    return java_name(False, name)
def java_field_type(spec, domain):
    return javaTypeMap[spec.resolveDomain(domain)]

def java_field_default_value(type, value):
    if type == 'int':
        return value
    elif type == 'boolean':
        return "{0}".format(value).lower()
    elif type == 'String':
        return "\"{0}\"".format(value)
    elif type == 'LongString':
        return "LongStringHelper.asLongString(\"{0}\")".format(value)
    elif type == 'long':
        return "{0}L".format(value)
    elif type == 'Map<String,Object>':
        return "null"
    else:
        raise BogusDefaultValue("JSON provided default value {0} for suspicious type {1}".format(value, type))

def typeNameDefault(spec, a):
    return (java_field_type(spec, a.domain),
            java_field_name(a.name),
            java_field_default_value(java_field_type(spec, a.domain),
                                     a.defaultvalue))

def nullCheckedFields(spec, m):
    fieldsToNullCheck = set([])
    for a in m.arguments:
        (jfType, jfName, jfDefault) = typeNameDefault(spec,a)
        if jfType in javaTypesToCheckForNull:
            fieldsToNullCheck.add(jfName)
    return fieldsToNullCheck

#---------------------------------------------------------------------------

def printFileHeader():
    print """//   NOTE: This -*- java -*- source code is autogenerated from the AMQP
//         specification!
//
//  The contents of this file are subject to the Mozilla Public License
//  Version 1.1 (the "License"); you may not use this file except in
//  compliance with the License. You may obtain a copy of the License
//  at http://www.mozilla.org/MPL/
//
//  Software distributed under the License is distributed on an "AS IS"
//  basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
//  the License for the specific language governing rights and
//  limitations under the License.
//
//  The Original Code is RabbitMQ.
//
//  The Initial Developer of the Original Code is VMware, Inc.
//  Copyright (c) 2007-2011 VMware, Inc.  All rights reserved.
//
"""

def genJavaApi(spec):
    def printHeader():
        printFileHeader()
        print "package com.rabbitmq.client;"
        print
        print "import java.io.IOException;"
        print "import java.util.Collections;"
        print "import java.util.HashMap;"
        print "import java.util.Map;"
        print "import java.util.Date;"
        print
        print "import com.rabbitmq.client.impl.ContentHeaderPropertyWriter;"
        print "import com.rabbitmq.client.impl.ContentHeaderPropertyReader;"
        print "import com.rabbitmq.client.impl.LongString;"
        print "import com.rabbitmq.client.impl.LongStringHelper;"

    def printProtocolClass():
        print
        print "    public static class PROTOCOL {"
        print "        public static final int MAJOR = %i;" % spec.major
        print "        public static final int MINOR = %i;" % spec.minor
        print "        public static final int REVISION = %i;" % spec.revision
        print "        public static final int PORT = %i;" % spec.port
        print "    }"

    def printConstants():
        print
        for (c,v,cls) in spec.constants: print "    public static final int %s = %i;" % (java_constant_name(c), v)

    def builder(c,m):
        def ctorCall(c,m):
            ctor_call = "com.rabbitmq.client.impl.AMQImpl.%s.%s" % (java_class_name(c.name),java_class_name(m.name))
            ctor_arg_list = [ java_field_name(a.name) for a in m.arguments ]
            print "                    return new %s(%s);" % (ctor_call, ", ".join(ctor_arg_list))

        def genFields(spec, m):
            for a in m.arguments:
                (jfType, jfName, jfDefault) = typeNameDefault(spec, a)
                if a.defaultvalue != None:
                    print "                private %s %s = %s;" % (jfType, jfName, jfDefault)
                else:
                    print "                private %s %s;" % (jfType, jfName)

        def genArgMethods(spec, m):
            for a in m.arguments:
                (jfType, jfName, jfDefault) = typeNameDefault(spec, a)

                if jfType == "Map<String,Object>":
                    print "                public Builder %s(%s %s)" % (jfName, jfType, jfName)
                    print "                {   this.%s = %s==null ? null : Collections.unmodifiableMap(new HashMap<String,Object>(%s)); return this; }" % (jfName, jfName, jfName)
                else:
                    print "                public Builder %s(%s %s)" % (jfName, jfType, jfName)
                    print "                {   this.%s = %s; return this; }" % (jfName, jfName)

                if jfType == "boolean":
                    print "                public Builder %s()" % (jfName)
                    print "                {   return this.%s(true); }" % (jfName)
                elif jfType == "LongString":
                    print "                public Builder %s(String %s)" % (jfName, jfName)
                    print "                {   return this.%s(LongStringHelper.asLongString(%s)); }" % (jfName, jfName)

        def genBuildMethod(c,m):
            print "                public %s build() {" % (java_class_name(m.name))
            ctorCall(c,m)
            print "                }"

        print
        print "            // Builder for instances of %s.%s" % (java_class_name(c.name), java_class_name(m.name))
        print "            public static final class Builder"
        print "            {"
        genFields(spec, m)
        print
        print "                public Builder() { }"
        print
        genArgMethods(spec, m)
        genBuildMethod(c,m)
        print "            }"

    def printClassInterfaces():
        for c in spec.classes:
            print
            print "    public static class %s {" % (java_class_name(c.name))
            for m in c.allMethods():
                print "        public interface %s extends Method {" % ((java_class_name(m.name)))
                for a in m.arguments:
                    print "            %s %s();" % (java_field_type(spec, a.domain), java_getter_name(a.name))
                builder(c,m)
                print "        }"
            print "    }"

    def printReadPropertiesFrom(c):
        print
        print """        public void readPropertiesFrom(ContentHeaderPropertyReader reader)
            throws IOException
        {"""
        for f in c.fields:
            print "            boolean %s_present = reader.readPresence();" % (java_field_name(f.name))
        print "            reader.finishPresence();"
        for f in c.fields:
            print "            this.%s = %s_present ? reader.read%s() : null;" % (java_field_name(f.name), java_field_name(f.name),  java_class_name(f.domain))
        print "        }"

    def printWritePropertiesTo(c):
        print
        print """        public void writePropertiesTo(ContentHeaderPropertyWriter writer)
            throws IOException
        {"""
        for f in c.fields:
            print "            writer.writePresence(this.%s != null);" % (java_field_name(f.name))
        print "            writer.finishPresence();"
        for f in c.fields:
            print "            if (this.%s != null) { writer.write%s(this.%s); }" % (java_field_name(f.name), java_class_name(f.domain), java_field_name(f.name))
        print "        }"

    def printAppendArgumentDebugStringTo(c):
        appendList = [ "%s=\")\n               .append(this.%s)\n               .append(\"" 
                       % (f.name, java_field_name(f.name))
                       for f in c.fields ]
        print
        print "        public void appendArgumentDebugStringTo(StringBuffer acc) {"
        print "            acc.append(\"(%s)\");" % ", ".join(appendList)
        print "        }"
        
    def printPropertiesClass(c):
        print
        print "    public static class %(className)s extends %(parentClass)s {" % {'className' : java_class_name(c.name) + 'Properties', 'parentClass' : 'com.rabbitmq.client.impl.AMQ' + java_class_name(c.name) + 'Properties'}
        #property fields
        for f in c.fields:
            print "        private %s %s;" % (java_property_type(spec, f.domain),java_field_name(f.name))

        #explicit constructor
        if c.fields:
            print
            consParmList = [ "%s %s" % (java_property_type(spec,f.domain),java_field_name(f.name))
                             for f in c.fields ]
            print "        public %sProperties(" % (java_class_name(c.name))
            print "            %s)" % (",\n            ".join(consParmList))
            print "        {"
            for f in c.fields:
                print "            this.%s = %s;" % (java_field_name(f.name), java_field_name(f.name))
            print "        }"

        #default constructor
        print
        print "        public %sProperties() {}" % (java_class_name(c.name))

        #class properties
        print "        public int getClassId() { return %i; }" % (c.index)
        print "        public String getClassName() { return \"%s\"; }" % (c.name)

        #accessor methods
        print
        for f in c.fields:
            print """        public %(fieldType)s get%(capFieldName)s() { return %(fieldName)s; }
        public void set%(capFieldName)s(%(fieldType)s %(fieldName)s) { this.%(fieldName)s = %(fieldName)s; }""" % \
            {'fieldType' : java_property_type(spec, f.domain), \
            'capFieldName' : (java_field_name(f.name)[0].upper() + java_field_name(f.name)[1:]), \
            'fieldName' : java_field_name(f.name)}

        printReadPropertiesFrom(c)
        printWritePropertiesTo(c)
        printAppendArgumentDebugStringTo(c)
        print "    }"

    def printPropertiesClasses():
        for c in spec.classes:
            if c.hasContentProperties:
                printPropertiesClass(c)

    printHeader()
    print
    print "public interface AMQP {"

    printProtocolClass()
    printConstants()
    printClassInterfaces()
    printPropertiesClasses()

    print "}"

#--------------------------------------------------------------------------------

def genJavaImpl(spec):
    def printHeader():
        printFileHeader()
        print "package com.rabbitmq.client.impl;"
        print
        print "import java.io.IOException;"
        print "import java.io.DataInputStream;"
        print "import java.util.Map;"
        print
        print "import com.rabbitmq.client.AMQP;"
        print "import com.rabbitmq.client.UnknownClassOrMethodId;"
        print "import com.rabbitmq.client.UnexpectedMethodError;"

    def printClassMethods(spec, c):
        print
        print "    public static class %s {" % (java_class_name(c.name))
        print "        public static final int INDEX = %s;" % (c.index)
        for m in c.allMethods():

            def getters():
                if m.arguments:
                    print
                    for a in m.arguments:
                        print "            public %s %s() { return %s; }" % (java_field_type(spec,a.domain), java_getter_name(a.name), java_field_name(a.name))

            def constructors():
                print
                argList = [ "%s %s" % (java_field_type(spec,a.domain),java_field_name(a.name)) for a in m.arguments ]
                print "            public %s(%s) {" % (java_class_name(m.name), ", ".join(argList))

                fieldsToNullCheckInCons = nullCheckedFields(spec, m)

                for f in fieldsToNullCheckInCons:
                    print "                if(%s == null)" % (f)
                    print "                    throw new IllegalStateException(\"Invalid configuration: '%s' must be non-null.\");" % (f)

                for a in m.arguments:
                    print "                this.%s = %s;" % (java_field_name(a.name), java_field_name(a.name))
                print "            }"

                consArgs = [ "rdr.read%s()" % (java_class_name(spec.resolveDomain(a.domain))) for a in m.arguments ]
                print "            public %s(MethodArgumentReader rdr) throws IOException {" % (java_class_name(m.name))
                print "                this(%s);" % (", ".join(consArgs))
                print "            }"

            def others():
                print
                print "            public int protocolClassId() { return %s; }" % (c.index)
                print "            public int protocolMethodId() { return %s; }" % (m.index)
                print "            public String protocolMethodName() { return \"%s.%s\";}" % (c.name, m.name)
                print
                print "            public boolean hasContent() { return %s; }" % (trueOrFalse(m.hasContent))
                print
                print "            public Object visit(MethodVisitor visitor) throws IOException"
                print "            {   return visitor.visit(this); }"

            def trueOrFalse(truthVal):
                if truthVal:
                    return "true"
                else:
                    return "false"

            def argument_debug_string():
                appendList = [ "%s=\")\n                   .append(this.%s)\n                   .append(\"" 
                               % (a.name, java_field_name(a.name))
                               for a in m.arguments ]
                print
                print "            public void appendArgumentDebugStringTo(StringBuffer acc) {"
                print "                acc.append(\"(%s)\");" % ", ".join(appendList)
                print "            }"

            def write_arguments():
                print
                print "            public void writeArgumentsTo(MethodArgumentWriter writer)"
                print "                throws IOException"
                print "            {"
                for a in m.arguments:
                    print "                writer.write%s(this.%s);" % (java_class_name(spec.resolveDomain(a.domain)), java_field_name(a.name))
                print "            }"

            #start
            print
            print "        public static class %s" % (java_class_name(m.name),)
            print "            extends Method"
            print "            implements com.rabbitmq.client.AMQP.%s.%s" % (java_class_name(c.name), java_class_name(m.name))
            print "        {"
            print "            public static final int INDEX = %s;" % (m.index)
            print
            for a in m.arguments:
                print "            private final %s %s;" % (java_field_type(spec, a.domain), java_field_name(a.name))

            getters()
            constructors()
            others()

            argument_debug_string()
            write_arguments()

            print "        }"
        print "    }"

    def printMethodVisitor():
        print
        print "    public interface MethodVisitor {"
        for c in spec.allClasses():
            for m in c.allMethods():
                print "        Object visit(%s.%s x) throws IOException;" % (java_class_name(c.name), java_class_name(m.name))
        print "    }"

        #default method visitor
        print
        print "    public static class DefaultMethodVisitor implements MethodVisitor {"
        for c in spec.allClasses():
            for m in c.allMethods():
               print "        public Object visit(%s.%s x) throws IOException { throw new UnexpectedMethodError(x); }" % (java_class_name(c.name), java_class_name(m.name))
        print "    }"

    def printMethodArgumentReader():
        print
        print "    public static Method readMethodFrom(DataInputStream in) throws IOException {"
        print "        int classId = in.readShort();"
        print "        int methodId = in.readShort();"
        print "        switch (classId) {"
        for c in spec.allClasses():
            print "            case %s:" % (c.index)
            print "                switch (methodId) {"
            for m in c.allMethods():
                fq_name = java_class_name(c.name) + '.' + java_class_name(m.name)
                print "                    case %s: {" % (m.index)
                print "                        return new %s(new MethodArgumentReader(in));" % (fq_name)
                print "                    }"
            print "                    default: break;"
            print "                } break;"
        print "        }"
        print
        print "        throw new UnknownClassOrMethodId(classId, methodId);"
        print "    }"

    def printContentHeaderReader():
        print
        print "    public static AMQContentHeader readContentHeaderFrom(DataInputStream in) throws IOException {"
        print "        int classId = in.readShort();"
        print "        switch (classId) {"
        for c in spec.allClasses():
            if c.fields:
                print "            case %s: return new %sProperties();" %(c.index, (java_class_name(c.name)))
        print "            default: break;"
        print "        }"
        print
        print "        throw new UnknownClassOrMethodId(classId, -1);"
        print "    }"

    printHeader()
    print
    print "public class AMQImpl implements AMQP {"

    for c in spec.allClasses(): printClassMethods(spec,c)
    
    printMethodVisitor()
    printMethodArgumentReader()
    printContentHeaderReader()

    print "}"

#--------------------------------------------------------------------------------

def generateJavaApi(specPath):
    genJavaApi(AmqpSpec(specPath))

def generateJavaImpl(specPath):
    genJavaImpl(AmqpSpec(specPath))

if __name__ == "__main__":
    do_main(generateJavaApi, generateJavaImpl)
