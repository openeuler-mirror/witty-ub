#include "urma_failure_260.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure260> g_urma("urma_260");

bool UrmaFailure260::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'init_matrix_slave_devices' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Primary eid is empty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure260::GetName() const
{
    return "init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure260::GetRootCauseDesc() const
{
    return "init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure260::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure260::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure260::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Primary eid is empty";
}

std::string UrmaFailure260::GetId() const
{
    return "urma_260";
}

} // namespace diag
