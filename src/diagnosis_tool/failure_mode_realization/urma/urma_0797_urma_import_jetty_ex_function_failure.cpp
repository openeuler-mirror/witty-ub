#include "urma_0797_urma_import_jetty_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0797UrmaImportJettyExFunctionFailure> g_urma("urma_0797");

bool Urma0797UrmaImportJettyExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0798"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0797UrmaImportJettyExFunctionFailure::GetName() const
{
    return "urma_import_jetty_ex 函数故障";
}

std::string Urma0797UrmaImportJettyExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0797UrmaImportJettyExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0797UrmaImportJettyExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0797UrmaImportJettyExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0797UrmaImportJettyExFunctionFailure::GetId() const
{
    return "urma_0797";
}
} // namespace diag
