#include "urma_failure_059.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure059> g_urma("urma_059");

bool UrmaFailure059::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_del_jfr_p_vjetty_info_without_lock' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete p_vjfr_id node[' | grep -F ']: ret' | grep -F 'pjfr_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure059::GetName() const
{
    return "虚拟 JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure059::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure059::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure059::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure059::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfr_p_vjetty_info_without_lock，Failed to delete p_vjfr_id node[，]: "
           "ret，pjfr_id:";
}

std::string UrmaFailure059::GetId() const
{
    return "urma_059";
}

} // namespace diag
