#include "urma_failure_567.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure567> g_urma("urma_567");

bool UrmaFailure567::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos;
}

std::string UrmaFailure567::GetName() const
{
    return "JFS无效导致删除JFS失败";
}

std::string UrmaFailure567::GetRootCauseDesc() const
{
    return "urma_delete_jfs_batch用于删除JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure567::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure567::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure567::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Invalid parameter, index:。";
}

std::string UrmaFailure567::GetId() const
{
    return "urma_567";
}
} // namespace diag
