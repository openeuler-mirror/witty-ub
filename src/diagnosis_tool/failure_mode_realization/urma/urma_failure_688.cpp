#include "urma_failure_688.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure688> g_urma("urma_688");

bool UrmaFailure688::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfs_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure688::GetName() const
{
    return "JFS、缓冲区、opt、len无效导致设置JFS失败";
}

std::string UrmaFailure688::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfs_opt用于设置JFS，调用方传入的JFS、缓冲区、opt、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure688::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure688::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure688::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfs_opt，Invalid parameter.。";
}

std::string UrmaFailure688::GetId() const
{
    return "urma_688";
}
} // namespace diag
