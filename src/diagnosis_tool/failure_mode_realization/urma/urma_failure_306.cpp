#include "urma_failure_306.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure306> g_urma("urma_306");

bool UrmaFailure306::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tpn' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter with max_netaddr_cnt as 0.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure306::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息无效导致获取TPN失败";
}

std::string UrmaFailure306::GetRootCauseDesc() const
{
    return "函数用于获取TPN，调用方传入的URMA "
           "context、设备对象、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure306::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure306::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure306::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tpn，Invalid parameter with max_netaddr_cnt as 0.。";
}

std::string UrmaFailure306::GetId() const
{
    return "urma_306";
}

} // namespace diag
