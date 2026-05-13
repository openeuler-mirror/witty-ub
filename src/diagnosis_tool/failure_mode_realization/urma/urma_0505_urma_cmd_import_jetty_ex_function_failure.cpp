#include "urma_0505_urma_cmd_import_jetty_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0505UrmaCmdImportJettyExFunctionFailure> g_urma("urma_0505");

bool Urma0505UrmaCmdImportJettyExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0506"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0505UrmaCmdImportJettyExFunctionFailure::GetName() const
{
    return "urma_cmd_import_jetty_ex 函数故障";
}

std::string Urma0505UrmaCmdImportJettyExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0505UrmaCmdImportJettyExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0505UrmaCmdImportJettyExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0505UrmaCmdImportJettyExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0505UrmaCmdImportJettyExFunctionFailure::GetId() const
{
    return "urma_0505";
}
} // namespace diag
