#include "urma_failure_571.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure571> g_urma("urma_571");

bool UrmaFailure571::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfs") != std::string::npos &&
           message.find("Failed to exec ops->deactive_jfs.") != std::string::npos;
}

std::string UrmaFailure571::GetName() const
{
    return "去激活JFS执行失败导致去激活JFS失败";
}

std::string UrmaFailure571::GetRootCauseDesc() const
{
    return "urma_deactive_jfs执行去激活JFS时依赖的去激活JFS步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure571::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure571::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure571::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，Failed to exec ops->deactive_jfs.。";
}

std::string UrmaFailure571::GetId() const
{
    return "urma_571";
}
} // namespace diag
