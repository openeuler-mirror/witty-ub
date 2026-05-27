#include "urma_failure_069.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure069> g_urma("urma_069");

bool UrmaFailure069::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info_without_lock' \"$URMA_LOG_PATH\" "
        "2>/dev/null | grep -F 'Failed to delete p_vjetty_id node: ret:' | grep -F 'pjetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure069::GetName() const
{
    return "虚拟 Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure069::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure069::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure069::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure069::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info_without_lock，Failed to delete "
           "p_vjetty_id node: ret:，pjetty_id:。";
}

std::string UrmaFailure069::GetId() const
{
    return "urma_069";
}

} // namespace diag
