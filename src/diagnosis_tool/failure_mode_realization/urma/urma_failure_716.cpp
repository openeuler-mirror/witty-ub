#include "urma_failure_716.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure716> g_urma("urma_716");

bool UrmaFailure716::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_open_cdev' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'file_path:' | grep -F 'is not standardize.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure716::GetName() const
{
    return "打开字符设备过程中依赖步骤失败";
}

std::string UrmaFailure716::GetRootCauseDesc() const
{
    return "函数用于打开字符设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure716::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure716::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure716::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_cdev，file_path:，is not standardize.。";
}

std::string UrmaFailure716::GetId() const
{
    return "urma_716";
}

} // namespace diag
