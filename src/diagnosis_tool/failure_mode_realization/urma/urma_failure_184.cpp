#include "urma_failure_184.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure184> g_urma("urma_184");

bool UrmaFailure184::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_trans_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:' | grep -F ', order_type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure184::GetName() const
{
    return "URMA context、设备对象、JFR对象无效导致创建Jetty失败";
}

std::string UrmaFailure184::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，调用方传入的URMA "
           "context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure184::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure184::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure184::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_trans_mode，Invalid parameter, trans_mode:，, "
           "order_type:。";
}

std::string UrmaFailure184::GetId() const
{
    return "urma_184";
}

} // namespace diag
