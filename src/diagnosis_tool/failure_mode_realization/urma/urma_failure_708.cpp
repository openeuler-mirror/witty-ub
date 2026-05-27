#include "urma_failure_708.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure708> g_urma("urma_708");

bool UrmaFailure708::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_open_cdev' "
                                                         "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'file_path:' | "
                                                         "grep -F 'is not standardize.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure708::GetName() const
{
    return "打开字符设备过程中依赖步骤失败";
}

std::string UrmaFailure708::GetRootCauseDesc() const
{
    return "函数用于打开字符设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure708::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure708::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure708::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_open_cdev，file_path:，is not standardize.";
}

std::string UrmaFailure708::GetId() const
{
    return "urma_708";
}

} // namespace diag
