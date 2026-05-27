#include "urma_failure_674.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure674> g_urma("urma_674");

bool UrmaFailure674::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to free jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure674::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure674::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure674::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure674::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure674::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfr，Failed to free jfr.。";
}

std::string UrmaFailure674::GetId() const
{
    return "urma_674";
}

} // namespace diag
