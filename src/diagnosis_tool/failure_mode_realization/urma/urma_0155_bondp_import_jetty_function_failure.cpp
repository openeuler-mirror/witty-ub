#include "urma_0155_bondp_import_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0155BondpImportJettyFunctionFailure> g_urma("urma_0155");

bool Urma0155BondpImportJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0156", "urma_0157", "urma_0158", "urma_0159",
                                                    "urma_0160", "urma_0161", "urma_0162", "urma_0163"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0155BondpImportJettyFunctionFailure::GetName() const
{
    return "bondp_import_jetty 函数故障";
}

std::string Urma0155BondpImportJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0155BondpImportJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0155BondpImportJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0155BondpImportJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0155BondpImportJettyFunctionFailure::GetId() const
{
    return "urma_0155";
}
} // namespace diag
