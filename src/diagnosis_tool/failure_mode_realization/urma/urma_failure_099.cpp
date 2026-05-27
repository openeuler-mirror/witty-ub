#include "urma_failure_099.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure099> g_urma("urma_099");

bool UrmaFailure099::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'handle_send_cr_with_store' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed find jetty when handle send cr, cr.local_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure099::GetName() const
{
    return "未找到可用于获取Jetty的有效对象或路由";
}

std::string UrmaFailure099::GetRootCauseDesc() const
{
    return "函数在获取Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure099::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure099::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure099::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_send_cr_with_store，Failed find jetty when handle send cr, "
           "cr.local_id:。";
}

std::string UrmaFailure099::GetId() const
{
    return "urma_099";
}

} // namespace diag
