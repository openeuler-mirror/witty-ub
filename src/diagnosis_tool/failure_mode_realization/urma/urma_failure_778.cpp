#include "urma_failure_778.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure778> g_urma("urma_778");

bool UrmaFailure778::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure778::GetName() const
{
    return "URMA context无效导致创建JFS失败";
}

std::string UrmaFailure778::GetRootCauseDesc() const
{
    return "函数用于创建JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure778::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure778::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure778::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_order_type，Invalid parameter.";
}

std::string UrmaFailure778::GetId() const
{
    return "urma_778";
}

} // namespace diag
