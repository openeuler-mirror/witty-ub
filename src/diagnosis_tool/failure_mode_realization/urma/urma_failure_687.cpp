#include "urma_failure_687.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure687> g_urma("urma_687");

bool UrmaFailure687::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure687::GetName() const
{
    return "JFS、URMA context、dev_fd、属性参数无效导致修改JFS失败";
}

std::string UrmaFailure687::GetRootCauseDesc() const
{
    return "urma_cmd_modify_jfs用于修改JFS，调用方传入的JFS、URMA "
           "context、dev_fd、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure687::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure687::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure687::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfs，Invalid parameter。";
}

std::string UrmaFailure687::GetId() const
{
    return "urma_687";
}
} // namespace diag
