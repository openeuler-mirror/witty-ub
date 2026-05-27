#include "urma_failure_608.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure608> g_urma("urma_608");

bool UrmaFailure608::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_vseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid param.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure608::GetName() const
{
    return "删除URMA资源所需输入对象无效导致删除Segment失败";
}

std::string UrmaFailure608::GetRootCauseDesc() const
{
    return "函数用于删除Segment，调用方传入的删除URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure608::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure608::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure608::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_vseg，invalid param.";
}

std::string UrmaFailure608::GetId() const
{
    return "urma_608";
}

} // namespace diag
