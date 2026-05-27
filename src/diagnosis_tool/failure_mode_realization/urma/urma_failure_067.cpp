#include "urma_failure_067.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure067> g_urma("urma_067");

bool UrmaFailure067::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_del_jetty_p_vjetty_info_without_lock' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete p_vjetty_id node: ret:' | grep -F 'pjetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure067::GetName() const
{
    return "虚拟 Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure067::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure067::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure067::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure067::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jetty_p_vjetty_info_without_lock，Failed to delete p_vjetty_id node: "
           "ret:，pjetty_id:";
}

std::string UrmaFailure067::GetId() const
{
    return "urma_067";
}

} // namespace diag
