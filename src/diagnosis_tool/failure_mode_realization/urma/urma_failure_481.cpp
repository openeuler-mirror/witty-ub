#include "urma_failure_481.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure481> g_urma("urma_481");

bool UrmaFailure481::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_jfc") != std::string::npos &&
           message.find("Invalid parameter, jfc is NULL in jfs_cfg.") != std::string::npos;
}

std::string UrmaFailure481::GetName() const
{
    return "Jetty、JFC无效导致创建Jetty、JFC失败";
}

std::string UrmaFailure481::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_"
           "jfc用于创建Jetty、JFC，调用方传入的Jetty、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure481::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure481::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure481::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_jfc，Invalid parameter, jfc is NULL in "
           "jfs_cfg.。";
}

std::string UrmaFailure481::GetId() const
{
    return "urma_481";
}
} // namespace diag
