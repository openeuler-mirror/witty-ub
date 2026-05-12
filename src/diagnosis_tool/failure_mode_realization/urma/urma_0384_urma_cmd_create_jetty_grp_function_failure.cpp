#include "urma_0384_urma_cmd_create_jetty_grp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0384UrmaCmdCreateJettyGrpFunctionFailure> g_urma("urma_0384");

bool Urma0384UrmaCmdCreateJettyGrpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0385"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0384UrmaCmdCreateJettyGrpFunctionFailure::GetName() const
{
    return "urma_cmd_create_jetty_grp 函数故障";
}

std::string Urma0384UrmaCmdCreateJettyGrpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0384UrmaCmdCreateJettyGrpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0384UrmaCmdCreateJettyGrpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0384UrmaCmdCreateJettyGrpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0384UrmaCmdCreateJettyGrpFunctionFailure::GetId() const
{
    return "urma_0384";
}
} // namespace diag
