#include "urma_failure_779.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure779> g_urma("urma_779");

bool UrmaFailure779::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure779::GetName() const
{
    return "URMA context无效导致创建JFS失败";
}

std::string UrmaFailure779::GetRootCauseDesc() const
{
    return "函数用于创建JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure779::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure779::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure779::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_order_type，Invalid parameter, trans_mode:";
}

std::string UrmaFailure779::GetId() const
{
    return "urma_779";
}

} // namespace diag
