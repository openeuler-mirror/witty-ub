#include "urma_failure_559.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure559> g_urma("urma_559");

bool UrmaFailure559::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_get_device_by_eid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'urma get device list failed!')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure559::GetName() const
{
    return "urma_get_device_by_eid 执行获取 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure559::GetRootCauseDesc() const
{
    return "urma_get_device_by_eid 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure559::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure559::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure559::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：urma get device list failed!";
}

std::string UrmaFailure559::GetId() const
{
    return "urma_559";
}

} // namespace diag
