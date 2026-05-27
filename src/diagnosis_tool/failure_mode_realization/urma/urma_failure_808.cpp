#include "urma_failure_808.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure808> g_urma("urma_808");

bool UrmaFailure808::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->deactive_jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure808::GetName() const
{
    return "去激活JFS过程中依赖步骤失败";
}

std::string UrmaFailure808::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure808::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure808::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure808::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，Failed to exec ops->deactive_jfs.。";
}

std::string UrmaFailure808::GetId() const
{
    return "urma_808";
}

} // namespace diag
