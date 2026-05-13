#ifndef FAILURE_MODE_H
#define FAILURE_MODE_H
#pragma once

#include <memory>
#include <string>
#include <vector>
namespace diag {
class RootCause {
public:
    RootCause(bool isFinalRootCauseInput, std::string rootCauseInput)
        : isFinalRootCause(isFinalRootCauseInput),
          rootCause(rootCauseInput)
    {
    }
    bool GetIsFinalRootCause();
    std::string GetRootCause();

private:
    bool isFinalRootCause;
    std::string rootCause;
};

class FailureMode {
public:
    virtual void PrintDesc();
    virtual std::string GetName() const = 0;
    virtual std::string GetValidationMethodDesc() const = 0;
    virtual bool IsValid(std::string& logContent) = 0;
    virtual std::string GetRootCauseDesc() const = 0;
    virtual RootCause AnalyzeRootCause();
    virtual std::string GetFixSuggDesc() const = 0;
    virtual std::string GetId() const = 0;
    void AddSubFailureMode(std::string faiureModeId);
    std::vector<std::string> GetSubFailureModes();

private:
    std::vector<std::string> subFailureModes;
};

} // namespace diag
#endif