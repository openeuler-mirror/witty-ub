#include "urma_failure_348.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure348> g_urma("urma_348");

bool UrmaFailure348::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'failed to add fd:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure348::GetName() const
{
    return "创建文件描述符过程中依赖步骤失败";
}

std::string UrmaFailure348::GetRootCauseDesc() const
{
    return "函数用于创建文件描述符，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次U"
           "RMA操作失败。";
}

RootCause UrmaFailure348::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure348::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure348::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pcontext，failed to add fd:，, errno:。";
}

std::string UrmaFailure348::GetId() const
{
    return "urma_348";
}

} // namespace diag
