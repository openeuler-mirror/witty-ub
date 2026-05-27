#include "urma_failure_054.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure054> g_urma("urma_054");

bool UrmaFailure054::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info_without_lock' \"$URMA_LOG_PATH\" "
        "2>/dev/null | grep -F 'Failed to delete p_vjfs_id node[' | grep -F ']: ret:' | grep -F 'pjfs_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure054::GetName() const
{
    return "虚拟 JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure054::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure054::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure054::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure054::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jfs_p_vjetty_info_without_lock，Failed to delete p_vjfs_id "
           "node[，]: ret:，pjfs_id:。";
}

std::string UrmaFailure054::GetId() const
{
    return "urma_054";
}

} // namespace diag
