#include "urma_failure_259.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure259> g_urma("urma_259");

bool UrmaFailure259::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'init_matrix_slave_devices' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to get topo info by bonding eid')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure259::GetName() const
{
    return "init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure259::GetRootCauseDesc() const
{
    return "init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure259::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure259::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure259::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get topo info by bonding eid";
}

std::string UrmaFailure259::GetId() const
{
    return "urma_259";
}

} // namespace diag
