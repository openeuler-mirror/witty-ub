#include "urma_failure_026.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure026> g_urma("urma_026");

bool UrmaFailure026::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_uninit' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete global context.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure026::GetName() const
{
    return "context清理阶段下层释放操作失败";
}

std::string UrmaFailure026::GetRootCauseDesc() const
{
    return "函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure026::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure026::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure026::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_uninit，Failed to delete global context.。";
}

std::string UrmaFailure026::GetId() const
{
    return "urma_026";
}

} // namespace diag
