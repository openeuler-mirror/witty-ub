#include "urma_failure_004.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure004> g_urma("urma_004");

bool UrmaFailure004::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("init_target_active_indices") != std::string::npos &&
           message.find("Failed to find connected port") != std::string::npos;
}

std::string UrmaFailure004::GetName() const
{
    return "初始化target、indices执行失败导致初始化target、indices失败";
}

std::string UrmaFailure004::GetRootCauseDesc() const
{
    return "init_target_active_indices初始化目标端有效端口索引时未找到可连通端口，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure004::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure004::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure004::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：init_target_active_indices，Failed to find connected port。";
}

std::string UrmaFailure004::GetId() const
{
    return "urma_004";
}
} // namespace diag
