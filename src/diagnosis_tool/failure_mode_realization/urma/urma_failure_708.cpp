#include "urma_failure_708.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure708> g_urma("urma_708");

bool UrmaFailure708::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfs_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure708::GetName() const
{
    return "JFS、缓冲区、len无效导致设置JFS失败";
}

std::string UrmaFailure708::GetRootCauseDesc() const
{
    return "urma_set_jfs_opt用于设置JFS，调用方传入的JFS、缓冲区、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure708::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure708::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure708::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfs_opt，Invalid parameter.。";
}

std::string UrmaFailure708::GetId() const
{
    return "urma_708";
}
} // namespace diag
