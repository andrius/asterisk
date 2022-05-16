IMAGE_NAME := andrius/asterisk

#	<Dockerfile>:<version>
# OR
#	<Dockerfile>:<version>,<tag1>,<tag2>,...
X86_IMAGES := \
	alpine-glibc:glibc_latest,alpine_glibc-18.x,glibc-18.x,alpine_glibc-18.2.2,glibc-18.2.2 \
	debian/18-current:18-current \
	debian/17.9.4:17.9.4 \
	debian/16-current:16-current \
	debian/16-certified:16-certified,16.8-cert \
	debian/13.38.3:13.38.3 \
	debian/13-certified:13-certified,13.21-cert \
	debian/15.7.4:15.7.4 \
	debian/14.7.8:14.7.8 \
	debian/12.8.2:12.8.2 \
	debian/11.25.3:11.25.3 \
	debian/10.12.4:10.12.4 \
	debian/1.8.32.3:1.8.32.3 \
	debian/1.6.2.24:1.6.2.24 \
	debian/1.4.44:1.4.44,1.4,1.4.44-debian,1.4-debian \
	centos/1.6.2.24:1.6.2.24 \
	centos/1.4.44:1.4.44 \
	centos/1.2.40:1.2.40,1.2,1.2.40-centos,1.2-centos

ALL_IMAGES := $(X86_IMAGES)



# Default is first image from ALL_IMAGES list.
DOCKERFILE ?= $(word 1,$(subst :, ,$(word 1,$(ALL_IMAGES))))
VERSION ?=  $(word 1,$(subst $(comma), ,\
                     $(word 2,$(subst :, ,$(word 1,$(ALL_IMAGES))))))
TAGS ?= $(word 2,$(subst :, ,$(word 1,$(ALL_IMAGES))))

no-cache ?= no

comma := ,
empty :=
space := $(empty) $(empty)
eq = $(if $(or $(1),$(2)),$(and $(findstring $(1),$(2)),\
                                $(findstring $(2),$(1))),1)



# Default Makefile rule:
# Make manual release of all supported Docker images to Docker Hub.
# Usage:
#	make all [no-cache=(yes|no)]

all: | release-all



# Make manual release of all supported Docker images to Docker Hub.
#
# Usage:
#	make release-all [no-cache=(yes|no)]

release-all:
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make release no-cache=$(no-cache) \
			DOCKERFILE=$(word 1,$(subst :, ,$(img))) \
			VERSION=$(word 1,$(subst $(comma), ,\
					 $(word 2,$(subst :, ,$(img))))) \
			TAGS=$(word 2,$(subst :, ,$(img))) ; \
	))



# Make manual release of Docker images to Docker Hub.
#
# Usage:
#	make release [no-cache=(yes|no)] [DOCKERFILE=] [VERSION=] [TAGS=t1,t2,...]

release: | post-push-hook post-checkout-hook image tags test push



# Build all supported Docker images.
#
# Usage:
#	make image-all

image-all:
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make image no-cache=$(no-cache) \
			DOCKERFILE=$(word 1,$(subst :, ,$(img))) \
			VERSION=$(word 1,$(subst $(comma), ,\
					 $(word 2,$(subst :, ,$(img))))) ; \
	))



# Build Docker image.
#
# Usage:
#	make image [no-cache=(yes|no)] [DOCKERFILE=] [VERSION=]

no-cache-arg = $(if $(call eq, $(no-cache), yes), --no-cache, $(empty))

image:
	docker build $(no-cache-arg) -t $(IMAGE_NAME):$(VERSION) $(DOCKERFILE) --build-arg VERSION=$(VERSION)



# Tag Docker image with given tags.
#
# Usage:
#	make tags [VERSION=] [TAGS=t1,t2,...]

parsed-tags = $(subst $(comma), $(space), $(TAGS))

tags:
	(set -e ; $(foreach tag, $(parsed-tags), \
		docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):$(tag) ; \
	))



# Manually push all supported Docker images to Docker Hub.

push-all:
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make push \
			TAGS=$(word 2,$(subst :, ,$(img))) ; \
	))



# Manually push Docker images to Docker Hub.
#
# Usage:
#	make push [TAGS=t1,t2,...]

push:
	(set -e ; $(foreach tag, $(parsed-tags), \
		docker push $(IMAGE_NAME):$(tag) ; \
		docker rmi ${IMAGE_NAME}:${tag} ; \
	))



# Create `post_push` Docker Hub hook.
#
# When Docker Hub triggers automated build all the tags defined in `post_push`
# hook will be assigned to built image. It allows to link the same image with
# different tags, and not to build identical image for each tag separately.
# See details:
# http://windsock.io/automated-docker-image-builds-with-multiple-tags
#
# Usage:
#	make post-push-hook [DOCKERFILE=] [TAGS=t1,t2,...]

post-push-hook:
	mkdir -p $(DOCKERFILE)/hooks
	docker run --rm -i -v $(PWD)/post_push.erb:/post_push.erb:ro \
		ruby:alpine erb -U \
			image_tags='$(TAGS)' \
		/post_push.erb > $(DOCKERFILE)/hooks/post_push



# Create `post_push` Docker Hub hook for all supported Docker images.
#
# Usage:
#	make post-push-hook-all

post-push-hook-all:
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make post-push-hook \
			DOCKERFILE=$(word 1,$(subst :, ,$(img))) \
			TAGS=$(word 2,$(subst :, ,$(img))) ; \
	))



# Create `post_checkout` Docker Hub hook.
#
# When Docker Hub triggers automated build, the `post_checkout` hook is called
# after the Git repo is checked out. This can be used to set up prerequisites
# for, for example, cross-platform builds.
# See details:
# https://docs.docker.com/docker-cloud/builds/advanced/#build-hook-examples
#
# Usage:
#	make post-checkout-hook [DOCKERFILE=]

post-checkout-hook:
	if [ -n "$(findstring /armhf/,$(DOCKERFILE))" ]; then \
		mkdir -p $(DOCKERFILE)/hooks; \
		docker run --rm -i -v $(PWD)/post_checkout.erb:/post_checkout.erb:ro \
			ruby:alpine erb -U \
				dockerfile='$(DOCKERFILE)' \
			/post_checkout.erb > $(DOCKERFILE)/hooks/post_checkout ; \
	fi


# Create `post_push` Docker Hub hook for all supported Docker images.
#
# Usage:
#	make post-checkout-hook-all

post-checkout-hook-all:
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make post-checkout-hook \
			DOCKERFILE=$(word 1,$(subst :, ,$(img))) ; \
	))



# Run tests for all supported Docker images.
#
# Usage:
#	make test-all [prepare-images=(no|yes)]

prepare-images ?= no

test-all:
ifeq ($(prepare-images),yes)
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make image no-cache=$(no-cache) \
			DOCKERFILE=$(word 1,$(subst :, ,$(img))) \
			VERSION=$(word 1,$(subst $(comma), ,\
					 $(word 2,$(subst :, ,$(img))))) ; \
	))
endif
	(set -e ; $(foreach img,$(ALL_IMAGES), \
		make test \
			DOCKERFILE=$(word 1,$(subst :, ,$(img))) \
			VERSION=$(word 1,$(subst $(comma), ,\
					 $(word 2,$(subst :, ,$(img))))) ; \
	))



# Run tests for Docker image.
#
# Usage:
#	make test [DOCKERFILE=] [VERSION=]

test: deps.bats
	DOCKERFILE=$(DOCKERFILE) IMAGE=$(IMAGE_NAME):$(VERSION) \
		./tests/bats/bin/bats -t ./tests/asterisk.bats



# Resolve project dependencies for running Bats tests.
#
# Usage:
#	make deps.bats [BATS_VER=]

BATS_VER ?= 1.5.0

deps.bats:
ifeq ($(wildcard $(PWD)/tests/bats),)
	mkdir -p $(PWD)/tests/bats
	wget https://github.com/bats-core/bats-core/archive/v$(BATS_VER).tar.gz \
		-O $(PWD)/tests/bats/bats.tar.gz
	tar -xzf $(PWD)/tests/bats/bats.tar.gz -C $(PWD)/tests/bats
	$(PWD)/tests/bats/bats-core-$(BATS_VER)/install.sh $(PWD)/tests/bats
	rm -rf  $(PWD)/tests/bats/bats.tar.gz \
		$(PWD)/tests/bats/bats-core-$(BATS_VER) \
		$(PWD)/tests/bats/share
endif



.PHONY: image tags push \
	image-all tags-all push-all \
        release release-all \
        post-push-hook post-push-hook-all \
	post-checkout-hook post-checkout-hook-all \
        test test-all deps.bats
