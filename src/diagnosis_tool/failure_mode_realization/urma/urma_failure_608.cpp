#include "urma_failure_608.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure608> g_urma("urma_608");

bool UrmaFailure608::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete_vjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure608::GetName() const
{
    return "虚拟 JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure608::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure608::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure608::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure608::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfr，Failed to delete_vjfr。";
}

std::string UrmaFailure608::GetId() const
{
    return "urma_608";
}

} // namespace diag
