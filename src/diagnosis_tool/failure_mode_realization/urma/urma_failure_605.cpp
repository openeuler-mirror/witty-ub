#include "urma_failure_605.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure605> g_urma("urma_605");

bool UrmaFailure605::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete pjfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure605::GetName() const
{
    return "物理 JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure605::GetRootCauseDesc() const
{
    return "函数负责释放或撤销物理 JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure605::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure605::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure605::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfs，Failed to delete pjfs。";
}

std::string UrmaFailure605::GetId() const
{
    return "urma_605";
}

} // namespace diag
