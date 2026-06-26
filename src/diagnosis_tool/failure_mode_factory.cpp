/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include "failure_mode_factory.h"
#include <iostream>
#include "failure_mode.h"

namespace diag {

FailureModeFactory &FailureModeFactory::Instance() noexcept
{
    static FailureModeFactory instance;
    return instance;
}

void FailureModeFactory::Register(const std::string &typeId, Creator creator) noexcept
{
    try {
        m_creators[typeId] = std::move(creator);
    } catch (...) {
        // 注册失败，但不抛异常
        std::terminate();
    }
}

std::shared_ptr<FailureMode> FailureModeFactory::Create(const std::string &typeId) const noexcept
{
    auto it = m_creators.find(typeId);
    if (it != m_creators.end()) {
        return it->second();
    }
    std::cout << "nullptr" << std::endl;
    return nullptr;
}

std::vector<std::string> FailureModeFactory::GetAllTypeIds() const noexcept
{
    std::vector<std::string> ids;
    ids.reserve(m_creators.size());
    for (const auto &[id, _] : m_creators) {
        ids.push_back(id);
    }
    return ids;
}

bool FailureModeFactory::IsRegistered(const std::string &typeId) const noexcept
{
    return m_creators.find(typeId) != m_creators.end();
}

} // namespace diag