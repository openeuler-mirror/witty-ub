#include "urma_failure_594.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure594> g_urma("urma_594");

bool UrmaFailure594::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pjfce' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete pjfce' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure594::GetName() const
{
    return "JFCE清理阶段下层释放操作失败";
}

std::string UrmaFailure594::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure594::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure594::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure594::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfce，Failed to delete pjfce，, ret:。";
}

std::string UrmaFailure594::GetId() const
{
    return "urma_594";
}

} // namespace diag
