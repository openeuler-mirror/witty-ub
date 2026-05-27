#include "urma_failure_511.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure511> g_urma("urma_511");

bool UrmaFailure511::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid token id for register bondp seg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure511::GetName() const
{
    return "URMA context、Segment对象无效导致注册Token失败";
}

std::string UrmaFailure511::GetRootCauseDesc() const
{
    return "函数用于注册Token，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure511::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure511::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure511::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vseg，Invalid token id for register bondp seg";
}

std::string UrmaFailure511::GetId() const
{
    return "urma_511";
}

} // namespace diag
