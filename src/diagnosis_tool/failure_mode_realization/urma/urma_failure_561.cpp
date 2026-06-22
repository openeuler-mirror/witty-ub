#include "urma_failure_561.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure561> g_urma("urma_561");

bool UrmaFailure561::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfs") != std::string::npos &&
           message.find("Failed to free jfs.") != std::string::npos;
}

std::string UrmaFailure561::GetName() const
{
    return "释放JFS执行失败导致释放JFS失败";
}

std::string UrmaFailure561::GetRootCauseDesc() const
{
    return "urma_free_jfs执行释放JFS时依赖的释放JFS步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure561::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure561::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure561::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfs，Failed to free jfs.。";
}

std::string UrmaFailure561::GetId() const
{
    return "urma_561";
}
} // namespace diag
