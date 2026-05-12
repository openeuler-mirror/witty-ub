#include "urma_0501_urma_cmd_import_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0501UrmaCmdImportJettyFunctionFailure> g_urma("urma_0501");

bool Urma0501UrmaCmdImportJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0502"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0501UrmaCmdImportJettyFunctionFailure::GetName() const
{
    return "urma_cmd_import_jetty 函数故障";
}

std::string Urma0501UrmaCmdImportJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0501UrmaCmdImportJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0501UrmaCmdImportJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0501UrmaCmdImportJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0501UrmaCmdImportJettyFunctionFailure::GetId() const
{
    return "urma_0501";
}
} // namespace diag
