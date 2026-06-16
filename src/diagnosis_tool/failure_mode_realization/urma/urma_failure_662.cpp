#include "urma_failure_662.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure662> g_urma("urma_662");

bool UrmaFailure662::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to free jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure662::GetName() const
{
    return "JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure662::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure662::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure662::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure662::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfs，Failed to free jfs.。";
}

std::string UrmaFailure662::GetId() const
{
    return "urma_662";
}

} // namespace diag
