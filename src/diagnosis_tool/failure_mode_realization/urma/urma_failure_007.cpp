#include "urma_failure_007.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure007> g_urma("urma_007");

bool UrmaFailure007::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'None of the providers registered'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure007::GetName() const
{
    return "urma_init 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure007::GetRootCauseDesc() const
{
    return "urma_init 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider "
           "注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure007::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure007::GetFixSuggDesc() const
{
    return "查看 `/usr/lib64/urma` 目录下是否存在 `liburma_udma.so` "
           "等驱动文件，确认文件具备执行权限，完成正确部署后重试";
}

std::string UrmaFailure007::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：None of the providers registered";
}

std::string UrmaFailure007::GetId() const
{
    return "urma_007";
}

} // namespace diag
