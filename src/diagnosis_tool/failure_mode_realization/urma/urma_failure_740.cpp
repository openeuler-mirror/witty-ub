#include "urma_failure_740.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure740> g_urma("urma_740");

bool UrmaFailure740::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'There is jfc event and it must be acked, jfc_comp:' | "
        "grep -F ', comp:' | "
        "grep -F ', jfc_async:' | "
        "grep -F ', async:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure740::GetName() const
{
    return "urma_cmd_delete_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure740::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。";
}

RootCause UrmaFailure740::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure740::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure740::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：There is jfc event and it must be acked, jfc_comp:, comp:, jfc_async:, "
           "async";
}

std::string UrmaFailure740::GetId() const
{
    return "urma_740";
}

} // namespace diag
