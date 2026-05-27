#include "urma_failure_180.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure180> g_urma("urma_180");

bool UrmaFailure180::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_trans_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure180::GetName() const
{
    return "URMA context、设备对象、JFR对象无效导致创建Jetty失败";
}

std::string UrmaFailure180::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，调用方传入的URMA "
           "context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure180::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure180::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure180::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_create_jetty_check_trans_mode，Invalid parameter, trans_mode:";
}

std::string UrmaFailure180::GetId() const
{
    return "urma_180";
}

} // namespace diag
