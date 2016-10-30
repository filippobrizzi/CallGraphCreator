#! /usr/bin/env python
#***********************************************************
#* Software License Agreement (BSD License)
#*
#*  Copyright (c) 2016, Filippo Brizzi.
#*  All rights reserved.
#*
#*  Redistribution and use in source and binary forms, with or without
#*  modification, are permitted provided that the following conditions
#*  are met:
#*
#*   * Redistributions of source code must retain the above copyright
#*     notice, this list of conditions and the following disclaimer.
#*   * Redistributions in binary form must reproduce the above
#*     copyright notice, this list of conditions and the following
#*     disclaimer in the documentation and/or other materials provided
#*     with the distribution.
#*   * Neither the name of Willow Garage, Inc. nor the names of its
#*     contributors may be used to endorse or promote products derived
#*     from this software without specific prior written permission.
#*
#*  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#*  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#*  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#*  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#*  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#*  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#*  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#*  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#*  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#*  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
#*  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#*  POSSIBILITY OF SUCH DAMAGE.
#*
#* Author: Filippo Brizzi
#***********************************************************

import sys
import os
import subprocess
import pydot
import string
import sets
import argparse
import time
import re

def getLabel(line):
	# if no [] means not a box
	if not '[' in line:
		return ""

	idx = line.find('label="')
	label = line[idx + 7:-1]
	if idx != -1:
		label = label.split('"', idx + 7)[0]
		return label
	return ""

def getNamesList(line):
	line = line.strip().replace(' ', '')
	if '[' in line:
		return [line.split('[')[0]]
	else:
		return line.split('->')


class CallGraphCreator:
	rm_policy = []
	reg_exp = -1
	rm_params = False
	rm_template = False
	rm_disconnected = False
	verbose = False

	def create(self, args):
		self.rm_template = args.remove_template
		self.rm_disconnected = args.remove_disconnected
		self.verbose = args.verbose
		self.setRmKeywork(args.regex, args.remove_keywords)
		if args.dot_file == None:
			self.createDot(args.cpp_file, args.include_dirs)
			args.dot_file = 'callgraph.dot'
		
		self.simplifyDot(args.dot_file, args.pdf)


	def createDot(self, cpp_file, include_dirs):
		includes = ''
		if include_dirs != None:
			for dir in include_dirs.split(','):
				includes = includes + '-I' + dir + ' '

		if self.verbose: print "Compilng c++ file to create the first dot file"
		cclang = 'clang++ -std=c++11 -S -emit-llvm ' + includes + ' ' + cpp_file + ' -o -'
		cllvm = 'opt -analyze -dot-callgraph' 
		pc = subprocess.Popen(cclang.split(), stdout=subprocess.PIPE)
		pl = subprocess.Popen(cllvm.split(),  stdin=pc.stdout, stdout=subprocess.PIPE)
		pc.stdout.close()
		output = pl.communicate()[0]

	def setRmKeywork(self, reguar_expression, keywords):
		if reguar_expression:
			self.reg_exp = re.compile(reguar_expression)

		if keywords != None:
			for w in keywords.split(','):
				self.rm_policy.append(w)

	def discard(self, label):
		if self.reg_exp != -1:
			if self.reg_exp.search(label) == None:
				return True

		for policy in self.rm_policy:
			if policy in label:
				return True
			
		return False

	
	def simplifyParameter(self, line):	
		#if not 'label="{' in line:
		#	return line
		if self.rm_params:
			return line.split('(')[0] + '}\n"'

		if self.rm_template:
			#check for shared_ptr or unique_ptr in that case skip
			if 'shared_ptr' in line or 'unique_ptr' in line:
				line = line.replace('<','[')
				line = line.replace('>',']')
			else:
				while True:
					id1 = line.find('<')
					id2 = line.find('>')
					if id1 > 0 and id2 > 0:
						opennum = line.count('<', id1+1, id2)
						for i in range(opennum):
							id2 = line.find('>', id2+1)

						line = line[0:id1] + line[id2+1:]
					else:
						break
		else:
			line = line.replace('<','__')
			line = line.replace('>','__')
		
		return line


	def simplifyDot(self, in_dot_file, out_pdf):
		
		new_in_dot_file = in_dot_file[0:-4] + "_new.dot"

		ccat = "cat " + in_dot_file
		cfilt = "c++filt"
		pc = subprocess.Popen(ccat.split(),  stdout=subprocess.PIPE)
		pf = subprocess.Popen(cfilt.split(), stdin=pc.stdout, stdout=subprocess.PIPE)
		pc.stdout.close()
		newdot = pf.communicate()[0]
		
		if self.verbose: print "Looking for node to be remved"
		rm_nodes = sets.Set()
		#for line in indot:
		for line in newdot.split('\n'):
			label = getLabel(line)
			# Search for node name
			if label and self.discard(label):
				name = getNamesList(line)[0]
				rm_nodes.add(name)

		print "Going to remove: ", len(rm_nodes)
		if self.verbose: print "Removing node in ban list"
		
		#for line in indot:
		newnewdot = ''
		for line in newdot.split('\n'):
			remove = False
			names = getNamesList(line)
			for name in names:
				if name in rm_nodes:
					remove = True
					break
				newnewdot += line
		
		graph = pydot.graph_from_dot_data(newnewdot)

		if self.verbose: print "Removing edges between nodes without label"
		for edge in graph.get_edge_list():
			source = edge.get_source()
			dest = edge.get_destination()
			snode = graph.get_node(source)
			dnode = graph.get_node(dest)
			if len(snode) == 0 or len(dnode) == 0:
				graph.del_edge(source, dest)

		if self.verbose: print "Simplifying labels"
		for node in graph.get_node_list():
			node.set_label(self.simplifyParameter(node.get_label()))

		if self.verbose: print "#nodes: ", len(graph.get_node_list())
		if self.verbose: print '#edges: ', len(graph.get_edge_list())

		if self.verbose: print "printing to pdf"
		graph.set('rankdir','TD')
		graph.set_suppress_disconnected(self.rm_disconnected)
		graph.set_strict(True)
		graph.write_pdf(out_pdf)



if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='if self.verbose: print the call graph of a c++ file\nThe system required clang and llvm to be installed')
	parser.add_argument('-c','--cpp_file',       help='The C++ source file')
	parser.add_argument('-I','--include_dirs',   help='The directories containing the include files needed to compile the source file, separated by a comma (,)')
	parser.add_argument('-d','--dot_file',		 help='If you already have a dot file and you want to simplify it instead of creating from a c++ file')
	parser.add_argument('-o','--pdf',  		     help='The name of the pdf where to store the graph')
	parser.add_argument('-r','--remove_keywords',help='List of keywords that if found in the label will cause the node to be discarderd. Specify multiple word separated by a comma (,)')
	parser.add_argument('-e','--regex',          help='Regular expression that determines wheter every node has valid labels to be kept in the final graph.')
	parser.add_argument('-p','--remove_parameter',   dest='remove_parameter',   action='store_true',help='Remove the parameter from the function definition in the nodes label')
	parser.add_argument('-t','--remove_template',    dest='remove_template',    action='store_true',help='Remove content of templates from the function definition in the nodes label')
	parser.add_argument('-s','--remove_disconnected',dest='remove_disconnected',action='store_true',help='Remove node that doesn\'t have edges')
	parser.add_argument('-v','--verbose',			 dest='verbose',			action='store_true',help='Enable verbose mode')
	parser.set_defaults(remove_parameter=False)
	parser.set_defaults(remove_template=False)
	parser.set_defaults(remove_disconnected=False)
	
	args = parser.parse_args()

	graph_crator = CallGraphCreator()
	graph_crator.create(args)