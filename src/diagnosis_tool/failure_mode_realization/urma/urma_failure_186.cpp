#include "urma_failure_186.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure186> g_urma("urma_186");

bool UrmaFailure186::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_trans_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfr is null or trans_mode or order_type invalid with shared jfr flag.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure186::GetName() const
{
    return "JFR对象无效导致创建JFR失败";
}

std::string UrmaFailure186::GetRootCauseDesc() const
{
    return "函数用于创建JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure186::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure186::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure186::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_trans_mode，jfr is null or trans_mode or "
           "order_type invalid with shared jfr flag.。";
}

std::string UrmaFailure186::GetId() const
{
    return "urma_186";
}

} // namespace diag
