#include "urma_failure_261.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure261> g_urma("urma_261");

bool UrmaFailure261::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'init_matrix_slave_devices' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'No port eid valid'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure261::GetName() const
{
    return "init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure261::GetRootCauseDesc() const
{
    return "init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure261::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure261::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure261::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：No port eid valid";
}

std::string UrmaFailure261::GetId() const
{
    return "urma_261";
}

} // namespace diag
