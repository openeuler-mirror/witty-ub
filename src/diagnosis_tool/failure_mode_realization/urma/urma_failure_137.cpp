#include "urma_failure_137.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure137> g_urma("urma_137");

bool UrmaFailure137::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfs") != std::string::npos &&
           message.find("Failed to add jfs p_vjetty_id info") != std::string::npos;
}

std::string UrmaFailure137::GetName() const
{
    return "创建JFS执行失败导致创建JFS失败";
}

std::string UrmaFailure137::GetRootCauseDesc() const
{
    return "bondp_create_jfs创建JFS时初始化端口索引或WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure137::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure137::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure137::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfs，Failed to add jfs p_vjetty_id info。";
}

std::string UrmaFailure137::GetId() const
{
    return "urma_137";
}
} // namespace diag
